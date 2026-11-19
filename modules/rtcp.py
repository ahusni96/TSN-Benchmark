from fabric import Result
from threading import Thread
from prettytable import PrettyTable

from modules.board import Board
from modules.runner import TestRunner

import modules.directories as dir
import sys, time

HOMEDIR: str = dir.get_homedir()

class RTCP_V2:
    def __init__(self,
                 runner: TestRunner,
                 type: str = "1ms",
                 duration: int = 60,
                 unit: str = "minute",
                 interval: int = 12,
                 stress: bool = True):
        self.RUNNER: TestRunner = runner
        self.TYPE: str = type
        self.DURATION: int = duration
        self.UNIT: str = unit
        self.INTERVAL: int = interval
        self.SETUP = self.RUNNER.SETUP
        self.RERUN = self.RUNNER.RERUN
        self.STRESS = stress

    def retrieve_log(self, board: Board, filename: str):
        board.connection.get(f'rtcp/{filename}', f'{self.RUNNER.OUTDIR}/{filename}')

    def show_mac(self, board: Board):
        try:
            res: Result = board.execute(f'ip link show dev {board.interface} | grep -i link/ether | xargs')
            mac = res.stdout.strip().split()[1]
            LOGGER.info(f'MAC Address {board.side}: {mac}')
        except Exception as e:
            LOGGER.info(f'Unable to fetch MAC Address from {board.side}-side')

    def change_mac(self, board: Board, mac: str = ''):
        try:
            board.execute(f'ip link set dev {board.interface} down')
            board.execute(f'ip link set dev {board.interface} addr {mac}')
            board.execute(f'ip link set dev {board.interface} up')
            self.show_mac(board)
        except:
            LOGGER.info(f'Unable to change MAC Address for {board.side}-side')

    def disable_services(self, board: Board):
        board.force_execute('systemctl disable --now apt-daily-upgrade.timer')
        board.force_execute('systemctl disable --now apt-daily.timer')
        board.force_execute('systemctl disable --now anacron.timer')
        board.force_execute('systemctl disable --now anacron.service')

    def system_setup(self, board: Board):
        board.connection.run('mkdir -p ~/rtcp')
        board.connection.put(f'{HOMEDIR}/rtcp/system-setup.sh', 'rtcp')

        with board.connection.cd('~/rtcp'):
            board.connection.run(f'chmod +x system-setup.sh')

            match board.side:
                case 'A':
                    board.execute(f'./system-setup.sh reference | tee ~/rtcp/setup-reference.log')
                    #self.retrieve_log(board, f'setup-reference.log')
                case 'B':
                    board.execute(f'./system-setup.sh mirror | tee ~/rtcp/setup-mirror.log')
                    #self.retrieve_log(board, f'setup-mirror.log')
                case _:
                    LOGGER.info('Invalid setup. Exiting...')
                    sys.exit(1)

    def system_tuning(self, board: Board):
        board.connection.run('mkdir -p ~/rtcp')
        board.connection.put(f'{HOMEDIR}/rtcp/system-tuning.sh', 'rtcp')

        with board.connection.cd('~/rtcp'):
            board.connection.run(f'chmod +x system-tuning.sh')
            board.execute(f'./system-tuning.sh {board.interface} | tee ~/rtcp/system-tuning-{board.side}.log')
            #self.retrieve_log(board, f'system-tuning-{board.side}.log')

    def configure_tsn(self, board: Board):
        with board.connection.cd(self.TPATH):
            match board.side:
                case 'A':
                    board.execute(f'./flow_ref.sh {board.interface} | tee ~/rtcp/flow_ref.log')
                    #self.retrieve_log(board, f'flow_ref.log')
                case 'B':
                    board.execute(f'./flow_mirror.sh {board.interface} | tee ~/rtcp/flow_mirror.log')
                    #self.retrieve_log(board, f'flow_mirror.log')
                case _:
                    LOGGER.info('Error occurred during TSN configuration. Exiting...')
                    sys.exit(1)

    def start_workloader(self, board: Board):
        match board.side:
            case 'A':
                board.force_execute(f'cd {self.TPATH} && ~/RTC-Testbench/build/reference -c reference.yaml > /dev/null &')
            case 'B':
                board.force_execute(f'cd {self.TPATH} && ~/RTC-Testbench/build/mirror -c mirror.yaml > /dev/null &')

    def stop_workloader(self, board: Board):
        match board.side:
            case 'A':
                board.force_execute(f'pkill reference')
            case 'B':
                board.force_execute(f'pkill mirror')
        board.force_execute(f'xdp-loader unload -a {board.interface}')

    def get_result(self, board: Board):
        match board.side:
            case 'A':
                res: Result = board.execute(f'tail -n 1 /var/log/reference_vid100.log', True)
                return self.result_formatting(res.stdout)
            case 'B':
                res: Result = board.execute(f'tail -n 1 /var/log/mirror_vid100.log', True)
                return self.result_formatting(res.stdout)

    def result_formatting(self, result: str):
        try:
            temp = result.split(':')
            return temp[2].split('|')
        except:
            return ['']

    def show_result(self):
        table = PrettyTable()
        column_1 = []
        column_2 = []
        column_3 = []
        column_4 = []

        try:
            for line in self.get_result(A):
                item = line.strip().split('=')
                if len(item) < 2:
                    continue
                column_1.append(item[0])
                column_2.append(item[1])

            for line in self.get_result(B):
                item = line.strip().split('=')
                if len(item) < 2:
                    continue
                column_3.append(item[0])
                column_4.append(item[1])

            if len(column_1) < len(column_3):
                diff = len(column_3) - len(column_1)
                for i in range(diff):
                    column_1.append('')
                    column_2.append('')
            else:
                diff = len(column_1) - len(column_3)
                for i in range(diff):
                    column_3.append('')
                    column_4.append('')

            table.add_column("Reference", column_1, 'l')
            table.add_column("Value(s)", column_2, 'r')
            table.add_column("Mirror", column_3, 'l')
            table.add_column("Value(s)", column_4, 'r')
        except:
            LOGGER.info(f'Unable to show results')
        LOGGER.info(table)

    def clear_rules(self, board: Board):
        board.execute(f'ethtool -K {board.interface} ntuple off')
        board.execute(f'ethtool -K {board.interface} ntuple on')

    def alt_run(self, board: Board):
        board.connection.put(f'{HOMEDIR}/rtcp/test-runner.sh', f'rtcp')
        board.execute(f'chmod +x ~/rtcp/test-runner.sh',)
        match board.side:
            case 'A':
                board.force_execute(f'~/rtcp/test-runner.sh reference {self.TPATH}')
            case 'B':
                board.force_execute(f'~/rtcp/test-runner.sh mirror {self.TPATH}')

    def validate_results(self, board: Board):
        try:
            failed = 0
            lines = self.get_result(board)
            if len(lines) < 1:
                return 'FAILED - lines less than 1'

            for line in lines:
                item = line.strip().split('=')
                if len(item) < 2:
                    continue
                match item[0]:
                    case 'TsnHighSent':
                        failed += 0 if int(item[1]) > 0 else 1
                        LOGGER.info(f'TsnHighSent = {item[1]}')
                    case 'TsnHighReceived':
                        failed += 0 if int(item[1]) > 0 else 1
                        LOGGER.info(f'TsnHighReceived = {item[1]}')
                    case 'TsnHighProcFirstOutliers':
                        failed += 1 if int(item[1]) > 0 else 0
                        LOGGER.info(f'TsnHighProcFirstOutliers = {item[1]}')
                    case 'TsnHighRttOutliers':
                        failed += 1 if int(item[1]) > 0 else 0
                        LOGGER.info(f'TsnHighRttOutliers = {item[1]}')
                    case 'TsnHighRxWorkloadOutliers':
                        failed += 1 if int(item[1]) > 0 else 0
                        LOGGER.info(f'TsnHighRxWorkloadOutliers = {item[1]}')

            if failed > 0:
                return 'FAILED - one or more item failed'
            else:
                return 'PASSED'
        except Exception as e:
            LOGGER.info(e)
            return 'FAILED - exception triggered'

    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER
        PATH = '~/RTC-Testbench/tests/intel_kpi/'

        LOGGER.info(f'##################################################################')
        LOGGER.info(f'##...........................RTCP 2.0.............................')

        try:
            match self.TYPE:
                case '1ms':
                    self.TEST = 'i226_xdp_1ms_1x64b_57k_proclat/'
                    self.TPATH = PATH + self.TEST
                case '125us':
                    self.TEST = 'i226_xdp_125us_1x64b_11k_proclat/'
                    self.TPATH = PATH + self.TEST
                case _:
                    LOGGER.info('Invalid test type. Exiting...')
                    sys.exit(1)

            if self.SETUP:
                LOGGER.info(f'##....................Platform Preparation........................')
                LOGGER.info(f'## Run system-setup script')

                T1: Thread = Thread(
                    target = self.system_setup,
                    args = (A,)
                )
                T2: Thread = Thread(
                    target = self.system_setup,
                    args = (B,)
                )

                T1.start()
                T2.start()

                T1.join()
                T2.join()

                LOGGER.info(f'\n## Copy XDP program to test directory')
                A.execute(f'cp ~/RTC-Testbench/build/xdp_kern_*.o {self.TPATH}')
                B.execute(f'cp ~/RTC-Testbench/build/xdp_kern_*.o {self.TPATH}')

                LOGGER.info(f'\nSetup completed, standby for 30 seconds before running the test.')
                time.sleep(30)
                LOGGER.info(f'Time elapsed: 30 second(s)\n')


            LOGGER.info(f'##.......................Test Execution...........................')

            if not self.RERUN:
                LOGGER.info(f'## Disable Services')
                self.disable_services(A)
                self.disable_services(B)

                time.sleep(3)

                LOGGER.info(f'\n## Change MAC Address')
                self.change_mac(A, 'a8:74:1d:9d:36:14')
                LOGGER.info('')
                self.change_mac(B, 'a8:74:1d:9d:98:d8')

                time.sleep(3)

                LOGGER.info(f'\n## Run system-tuning script')
                T1: Thread = Thread(
                    target = self.system_tuning,
                    args = (A,)
                )
                T2: Thread = Thread(
                    target = self.system_tuning,
                    args = (B,)
                )

                T1.start()
                T2.start()

                T1.join()
                T2.join()

                time.sleep(3)

                LOGGER.info(f'\n## Set Link Speed')
                A.execute(f'ethtool -s {A.interface} speed 1000 autoneg on duplex full')
                B.execute(f'ethtool -s {B.interface} speed 1000 autoneg on duplex full')

                time.sleep(3)

                LOGGER.info(f'\n## Disable rx and tx off-loading')
                A.execute(f'ethtool -K {A.interface} rxvlan off txvlan off')
                B.execute(f'ethtool -K {B.interface} rxvlan off txvlan off')

                time.sleep(3)

                LOGGER.info(f'\n## Clear rules')
                self.clear_rules(A)
                self.clear_rules(B)

                time.sleep(3)

                LOGGER.info(f'\n## Start Clock Sync')
                A.force_execute(f'~/RTC-Testbench/scripts/ptp.sh {A.interface} &')
                B.force_execute(f'~/RTC-Testbench/scripts/ptp.sh {B.interface} &')

                time.sleep(30)

                LOGGER.info(f'\n## Configure TSN')
                P1: Thread = Thread(
                    target = self.configure_tsn,
                    args = (A,)
                )
                P2: Thread = Thread(
                    target = self.configure_tsn,
                    args = (B,)
                )

                P2.start()
                P1.start()

                P1.join()
                P2.join()

                time.sleep(60)

            LOGGER.info('\n## Start workloader')
            P3: Thread = Thread(
                target = self.alt_run,
                args = (A,)
            )
            P4: Thread = Thread(
                target = self.alt_run,
                args = (B,)
            )

            if self.STRESS:
                B.force_execute(f'stress-ng --taskset 2-3 --cpu 2 --cpu-load 100 -t 0 > /dev/null &')

            P4.start()
            P3.start()

            P4.join()
            P3.join()

            LOGGER.info('')

            for i in range(self.INTERVAL):
                match self.UNIT:
                    case 'minute':
                        time.sleep(60 * (self.DURATION / self.INTERVAL))
                    case 'hour':
                        time.sleep(60 * 60)
                LOGGER.info(f'Time elapsed: {(i + 1) * (self.DURATION / self.INTERVAL)} {self.UNIT}(s)')
                self.show_result()

            LOGGER.info(f'\n## Kill processes after duration ends')
            self.stop_workloader(A)
            self.stop_workloader(B)
            B.pkill('stress-ng')

            LOGGER.info(f'\n## Validate Results')
            LOGGER.info(self.validate_results(B))

        except KeyboardInterrupt:
            self.stop_workloader(A)
            self.stop_workloader(B)
            B.pkill('stress-ng')
            LOGGER.info(f'Testing has been stopped manually...')
            LOGGER.info(f'STOPPED')

        except Exception as err:
            self.stop_workloader(A)
            self.stop_workloader(B)
            B.pkill('stress-ng')
            LOGGER.info(err)
            LOGGER.info(f'FAILED - An exception has occured at the main function')
