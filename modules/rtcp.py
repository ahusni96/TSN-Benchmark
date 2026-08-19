from fabric import Result
from datetime import timezone
from tabulate import tabulate
from threading import Thread

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner

import modules.directories as dir
import modules.shared as shared
import datetime, os, time


HOMEDIR: str = dir.get_homedir()

class RTCP_V1:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def get_rtcp_stat(self, board: Board):
        try:
            board.connection.get('/tmp/rtcp_statistic', 'temp')
        except:
            return

        with open('temp/rtcp_statistic') as file:
            lines = file.readlines()

    def check_result(self, board: Board):
        with open(f'{OUTDIR}/{board.platform}_{self.set_device(board.controller)}_{board.side.upper()}-side.txt') as f:
            text = 'Calculating RTCP results...'
            lines = f.readlines()

            for i in range(len(lines)):
                if lines[i].strip() == text:
                    HEADERS = lines[i + 2].strip().split()
                    ROW1 = lines[i + 3].strip().split()
                    ROW2 = lines[i + 4].strip().split()
                    ROW3 = lines[i + 5].strip().split()

                    table = tabulate([ROW1, ROW2, ROW3], HEADERS)
                    LOGGER.info(table)
                    LOGGER.info('')
                    LOGGER.info(lines[i + 7].strip())
                    LOGGER.info(lines[i + 8].strip())
                    LOGGER.info(lines[i + 9].strip())
                i += 1

            f.close()

    def set_packets(self, platform: str) -> str:
        match(platform):
            case 'ehl' | 'tglu' | 'tglh':
                return '100000'
            case 'adln':
                return '250000'
            case _:
                return '2400000'

    def set_device(self, controller: str) -> str:
        match(controller.lower()):
            case 'i225' | 'i226':
                return 'i225'
            case _:
                return 'dwmac'

    def msr(self, board: Board):
        if os.path.exists(f'{OUTDIR}/msr-tools-{board.side.lower()}'):
            os.remove(f'{OUTDIR}/msr-tools-{board.side.lower()}')

        if board.os == 'ubuntu':
            board.execute('apt update && apt install -y msr-tools')
        else:
            board.connection.put(f'{HOMEDIR}/files/msr-tools.zip', f'{board.home}/')
            board.execute(f'unzip {board.home}/msr-tools.zip')

            cmd: str = [
                'autoreconf --force --install --warnings=all',
                './configure $args "$@"',
                'make clean',
                'make',
                'make install'
            ]

            with board.connection.cd(f'{board.home}/msr-tools/'):
                for item in cmd:
                    res: Result = board.execute(item)
                    shared.save_output(OUTDIR, f'msr-tools-{board.side.lower()}', res.stdout.strip(), 'a')


    def setup(self, board: Board, device: str = 'dwmac'):
        # device : {i225, dwmac}
        board.platform = 'rpls'
        cmd = f'./rtcp.sh -p {board.platform.lower()} -h {self.set_device(board.controller)} -i {board.interface} -c rtcp1{board.side.lower()} -n {self.set_packets(board.platform)} -d 125000'

        if board.os == 'yocto':
            with board.connection.cd(f'{board.home}/rtcp-xdp/'):
                with board.connection.prefix(f'export PATH="{board.home}/msr-tools:$PATH"'):
                    with open(f'{OUTDIR}/setup-{board.side}.txt', 'w') as file:
                        res: Result = board.execute(cmd)
                        file.write(res.stdout.strip())
                        res: Result = board.execute('./rtcp.sh -S')
                        file.write(f'\n{res.stdout.strip()}')
        else:
            with board.connection.cd(f'{board.home}/rtcp-xdp/'):
                with open(f'{OUTDIR}/setup-{board.side}.txt', 'w') as file:
                    res: Result = board.execute(cmd)
                    file.write(res.stdout.strip())
                    res: Result = board.execute('./rtcp.sh -S')
                    file.write(f'\n{res.stdout.strip()}')


    def run(self, board: Board, device: str = 'dwmac'):
        if board.os == 'yocto':
            with board.connection.cd(f'{board.home}/rtcp-xdp/'):
                with board.connection.prefix(f'export PATH="{board.home}/msr-tools:$PATH"'):
                    result: Result = board.execute('./rtcp.sh -R')
                    with open(f'{OUTDIR}/{board.platform}_{self.set_device(board.controller)}_{board.side.upper()}-side.txt', 'w') as f:
                        f.write(result.stdout.strip())
                        f.close()
        else:
            with board.connection.cd(f'{board.home}/rtcp-xdp/'):
                result: Result = board.execute('./rtcp.sh -R')
                with open(f'{OUTDIR}/{board.platform}_{self.set_device(board.controller)}_{board.side.upper()}-side.txt', 'w') as f:
                    f.write(result.stdout.strip())
                    f.close()


    #def timedatectl(boards: list [Board]):
    #    dt = datetime.datetime.now()
    #
    #    A = boards[0]
    #    B = boards[1]
    #
    #    cmd = f'timedatectl set-ntp false'
    #    result: Result = A.execute(cmd)
    #    result: Result = B.execute(cmd)
    #
    #    A.execute(f'timedatectl set-time \'{dt.strftime("%Y-%m-%d %H:%M:%S")}\'')
    #    B.execute(f'timedatectl set-time \'{dt.strftime("%Y-%m-%d %H:%M:%S")}\'')
    #
    #    result: Result = A.execute('timedatectl')
    #    LOGGER.info(result.stdout.strip())
    #    result: Result = B.execute('timedatectl')
    #    LOGGER.info(result.stdout.strip())


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER

        #DUAL = False
        SETUP = True

        setup_A = Thread(target = self.setup, args = (A, 'i225'))
        setup_B = Thread(target = self.setup, args = (B, 'i225'))

        run_A = Thread(target = self.run, args = (A, 'i225'))
        run_B = Thread(target = self.run, args = (B, 'i225'))

        if SETUP:
            #timedatectl([A, B])

            setup_A.start()
            setup_B.start()

            setup_A.join()
            setup_B.join()

            time.sleep(10)

        #start_time = time.time()

        run_B.start()
        time.sleep(1)
        run_A.start()

        run_A.join()
        run_B.join()

        #LOGGER.info(f'\nTOTAL DURATION: {shared.duration(start_time, time.time())}\n')

        A.pkill('phc2sys')
        B.pkill('phc2sys')

        A.pkill('ptp4l')
        B.pkill('ptp4l')

        A.execute('systemctl restart NetworkManager')
        B.execute('systemctl restart NetworkManager')

        # From output file find this line for the table -> Calculating RTCP results...
        # For passing:
        # - IFD Avg cannot be more than duration set
        # - RTCP Max cannot be more than IFD Avg

        #check_result(B)

        return 'PASSED'

class RTCP_V2:
    def __init__(self, runner: TestRunner, type: str = "1ms", duration: int = 300):
        self.RUNNER: TestRunner = runner
        self.TYPE: str = type
        self.DURATION: int = duration


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER

        LOGGER.info(f'###\tRTCP 2.0')

        # Platform setup handled by bash script

        LOGGER.header('Run system-tuning script')
        # ./system-tuning.sh <INTERFACE>

        # 125us
        # cd ~/RTC-Testbench/tests/intel_kpi/i226_xdp_125us_1x64b_11k_proclat/

        # 1ms
        # cd ~/RTC-Testbench/tests/intel_kpi/i226_xdp_1ms_1x64b_57k_proclat/

        # Copy XDP Program
        # ~/RTC-Testbench/build/xdp_kern_*.o .

        # Start Clock Sync
        # ~/RTC-Testbench/scripts/ptp.sh <INTERFACE>

        # Start benchmark (around same time)
        # ./flow_mirror.sh <INTERFACE>
        # ./flow_ref.sh <INTERFACE>

        # Start workloader (around same time)
        # ../../../build/mirror -c mirror.yaml 2> mir.log &
        # ../../../build/reference -c reference.yaml 2> ref.log &

        return 'PASSED'
