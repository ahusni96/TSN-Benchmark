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

class Case10:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def init(self, board: Board, option: str):
        cmd = f'cd {TSN_PATH} && ' + f'./run.sh {board.platform} {board.interface} {option} init'

        if board.controller.lower() == 'i225':
            cmd = f'cd {TSN_PATH} && ' + f'./run.sh i225 {board.interface} {option} init'

        try:
            res: Result = board.execute(cmd)
            shared.save_output(OUTDIR, f'init_{board.side}', res.stdout.strip())

            if res.return_code == 0:
                LOGGER.info(f'Init {board.side}-side completed')

        except:
            LOGGER.error(f'Failed to init from {board.side}-side')


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
            LOGGER.error(e.result.stderr.strip())
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
            LOGGER.error(e.result.stderr.strip())
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

                _index = _lines.index('Transfer Complete')
                LOGGER.info(_lines[_index + 3])
                LOGGER.info(_lines[_index + 4])
                LOGGER.info(_lines[_index + 5])
                LOGGER.info(_lines[_index + 6])
                LOGGER.info(_lines[_index + 7])
                LOGGER.info(_lines[_index + 8])

                _result = _lines[_index + 4].split()
                _max = _result[1]
                _avg = _result[2]
                _loss = _result[9]

                # Add to fail count if condition is true
                if float(_loss) < 0 or float(_loss) > 10000:
                    _fail_count += 1

                if float(_avg) < 0 or float(_avg) > 1000000:
                    _fail_count += 1

                if float(_max) < 0 or float(_max) > 3150000:
                    _fail_count += 1

                # Consider failed if fail_counter more than zero
                if _fail_count > 0:
                    LOGGER.info('\nFAILED')
                    return 'FAILED'
                else:
                    LOGGER.info('\nPASSED')
                    return 'PASSED'
        except:
            LOGGER.info('Unable to validate results')
            return ''


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER, DUAL

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER
        DUAL = False

        A.set_logger(LOGGER)
        B.set_logger(LOGGER)

        LOGGER.info(f'###\tChapter 10 - OPCUA Simple Publish-Subscribe')

        LOGGER.header('Initiating OPCUA-PACKET')
        a = Thread(target=self.init, args=(A, 'opcua-pkt1a',))
        b = Thread(target=self.init, args=(B, 'opcua-pkt1b',))

        a.start()
        b.start()

        a.join()
        b.join()

        LOGGER.header('Setting up OPCUA-PACKET')
        a = Thread(
            target = self.setup,
            args = (A, 'opcua-pkt1a',)
        )
        b = Thread(
            target = self.setup,
            args = (B, 'opcua-pkt1b',)
        )

        a.start()
        b.start()

        a.join()
        b.join()

        LOGGER.header('Running OPCUA-PACKET')
        a = Thread(
            target = self.run,
            args = (A, 'opcua-pkt1a',)
        )
        b = Thread(
            target = self.run,
            args = (B, 'opcua-pkt1b',)
        )

        b.start()
        time.sleep(1)
        a.start()

        a.join()
        b.join()

        LOGGER.header('Kill remaining processes')
        A.pkill('phc2sys')
        A.pkill('ptp4l')
        B.pkill('phc2sys')
        B.pkill('ptp4l')

        LOGGER.header('Restart NetworkManager')
        A.force_execute('systemctl restart NetworkManager')
        B.force_execute('systemctl restart NetworkManager')

        LOGGER.header('Validate results')
        return self.validate_result()
