from fabric import Result
from threading import Thread
import time, sys

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner
import modules.directories as dir
import modules.shared as shared

from invoke.exceptions import Failure

HOMEDIR = dir.get_homedir()
TSN_PATH = '/usr/share/iotg-tsn-ref-sw/'
SLEEP = 3.5

### Notes
# iperf3 = 3.14-1
#   libiperf0 = 3.14-1
# iproute2 = 6.5.0-ppa1~noble2
#   libbpf9999 = 0.7.0-1ppa1~noble1
# ethtool = 6.7.1ppa1~noble3

### PTL
# ethtool -K $iface rxvlan off

class Case09:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def setup(self, board: Board, option: str):
        cmd = f'cd {TSN_PATH} && ' + f'./run.sh {board.platform} {board.interface} {option} setup'

        if board.controller.lower() == 'i225':
            cmd = f'cd {TSN_PATH} && ' + f'./run.sh i225 {board.interface} {option} setup'

        try:
            res: Result = board.execute(cmd)
            shared.save_output(OUTDIR, f'setup_{board.side}', res.stdout.strip())

            if res.return_code == 0:
                LOGGER.info(f'Setup {board.side}-side completed')
        except Failure as e:
            LOGGER.error(e.result.stderr)
            LOGGER.error(f'Failed to setup from {board.side}-side')
            sys.exit(1)
        except:
            LOGGER.error(f'Failed to run from {board.side}-side')
            sys.exit(1)


    def run(self, board: Board, option: str):
        cmd = f'cd {TSN_PATH} && ' + f'./run.sh {board.platform} {board.interface} {option} run'

        if board.controller.lower() == 'i225':
            cmd = f'cd {TSN_PATH} && ' + f'./run.sh i225 {board.interface} {option} run'

        try:
            res: Result = board.execute(cmd)
            shared.save_output(OUTDIR, f'run_{board.side}', res.stdout.strip())

            if res.return_code == 0:
                LOGGER.info(f'Run {board.side}-side completed')

        except Failure as e:
            LOGGER.error(e.result.stderr)
            LOGGER.error(f'Failed to run from {board.side}-side')
            sys.exit(1)
        except:
            LOGGER.error(f'Failed to run from {board.side}-side')
            sys.exit(1)


    def validate_result(self) -> str:
        try:
            with open(OUTDIR + '/run_B.txt') as file:
                _fail_count = 0
                _lines = file.readlines()

                for i in range(len(_lines)):
                    _lines[i] = _lines[i].strip()

                _index = _lines.index('PHASE 3: Calculating..')
                LOGGER.info(_lines[_index + 1])
                LOGGER.info(_lines[_index + 2])
                LOGGER.info(_lines[_index + 3]) # AF-PACKET values
                LOGGER.info(_lines[_index + 4])
                LOGGER.info(_lines[_index + 5])
                LOGGER.info(_lines[_index + 6]) # AF-XDP values
                LOGGER.info(_lines[_index + 7])

                _afpkt = _lines[_index + 3]
                _afxdp = _lines[_index + 6]

                _max_pkt = _afpkt.split()[1]
                _max_xdp = _afxdp.split()[1]

                if float(_max_pkt) < 0:
                    _fail_count += 1

                if float(_max_xdp) < 0:
                    _fail_count += 1

                if float(_max_xdp) > float(_max_pkt):
                    _fail_count += 1

                if float(_max_xdp) > 1000000:
                    _fail_count += 1

                if _fail_count > 0:
                    LOGGER.info('\nFAILED')
                    return 'FAILED'
                else:
                    LOGGER.info('\nPASSED')
                    return 'PASSED'

        except:
            LOGGER.error('Unable to verify results')
            return ''


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER, DUAL, RERUN

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER
        DUAL = False
        RERUN = False

        A.set_logger(LOGGER)
        B.set_logger(LOGGER)

        LOGGER.info(f'###\tChapter 9 - Bounded Low-latency Transmit/Receive (deprecated)')

        LOGGER.header('Turn off rxvlan - PTL Only')
        try:
            A.execute(f'ethtool -K {A.interface} rxvlan off')
            B.execute(f'ethtool -K {B.interface} rxvlan off')
        except:
            sys.exit(1)

        if not RERUN:
            LOGGER.header('Setting up TXRX-TSN')
            p1 = Thread(
                target = self.setup,
                args = (A, 'vs1a')
            )
            p2 = Thread(
                target = self.setup,
                args = (B, 'vs1b')
            )

            p1.start()
            p2.start()

            p1.join()
            p2.join()

        LOGGER.header('Running TXRX-TSN')
        p1 = Thread(
            target = self.run,
            args = (B, 'vs1b',)
        )
        p2 = Thread(
            target = self.run,
            args = (A, 'vs1a',)
        )

        p1.start()
        time.sleep(SLEEP)
        p2.start()

        p1.join()
        p2.join()

        LOGGER.header('Kill remaining processes')
        A.pkill('phc2sys')
        A.pkill('ptp4l')
        B.pkill('phc2sys')
        B.pkill('ptp4l')

        #LOGGER.header('Restart NetworkManager')
        #A.force_execute('systemctl restart NetworkManager')
        #B.force_execute('systemctl restart NetworkManager')

        LOGGER.header('Validating results')
        return self.validate_result()

