# Documentation: https://linutronix.github.io/RTC-Testbench

from invoke.runners import Result, Promise
from threading import Thread
import sys, time

from modules.board import Board
from modules.runner import TestRunner

import modules.directories as dir
import modules.setup as setup
import modules.shared as shared

HOMEDIR = dir.get_homedir()
WDIR = '/root/RTC-Testbench'
TEST = 'profinet'
STATUS = {
    "isMirrorRunning": False,
    "isClientRunning": False
}

class RTCP_V1:
    # Dependencies:
    # kernel < 6.16
    # iproute2 : 6.5.0-ppa1~noble2

    pass

class RTCP_V2:
    # Dependencies:
    # kernel >= 6.16
    # iproute2 : 6.5.0-ppa1~noble5

    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def sync_ptp(self, board: Board):
        # Not needed when doing reruns (runs in the background)
        try:
            with board.connection.cd(f'{WDIR}/tests/{TEST}'):
                board.force_execute(f'../../scripts/ptp.sh {board.interface}')
                time.sleep(60)
        except:
            pass

    def configure_traffic_flow(self, board: Board):
        # Not needed when doing reruns (one time after ptp sync)
        try:
            with board.connection.cd(f'{WDIR}/tests/{TEST}'):
                board.force_execute(f'./flow.sh {board.interface}')
                time.sleep(60)
        except:
            pass

    def start_mirror(self, board: Board):
        # B-side
        try:
            with board.connection.cd(f'{WDIR}/tests/{TEST}'):
                board.connection.run(f'cp ../../build/xdp_kern_*.o .')
                promise: Promise = board.async_execute(f'../../build/mirror -c mirror.yaml')
                STATUS['isMirrorRunning'] = True
                result: Result = promise.join()
                shared.save_output(OUTDIR, 'mirror', result.stdout)
                STATUS['isMirrorRunning'] = False
        except:
            pass

    def start_client(self, board: Board):
        # A-side
        try:
            with board.connection.cd(f'{WDIR}/tests/{TEST}'):
                board.connection.run(f'cp ../../build/xdp_kern_*.o .')
                promise: Promise = board.async_execute(f'../../build/reference -c reference.yaml')
                STATUS['isClientRunning'] = True
                result: Result = promise.join()
                shared.save_output(OUTDIR, 'reference', result.stdout)
                STATUS['isClientRunning'] = False
        except:
            pass

    def start_tail(self, board: Board, filename: str):
        try:
            board.connection.run(f'tail -f /var/log/{filename}.log')
        except:
            pass

    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER, DUAL, SETUP

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER
        DUAL = False
        RERUN = False

        A.set_logger(LOGGER)
        B.set_logger(LOGGER)

        LOGGER.info(f'###\tRTC-Benchmark (RTCP 2.0)')

        if not RERUN:
            LOGGER.header('PTP Synchronization')
            P1 = Thread(
                target = self.sync_ptp,
                args = (A,)
            )
            P2 = Thread(
                target = self.sync_ptp,
                args = (B,)
            )

            #P1.start()
            #P2.start()

            #P1.join()
            #P2.join()

            LOGGER.header('Traffic flow configurations')
            P1 = Thread(
                target = self.configure_traffic_flow,
                args = (A,)
            )
            P2 = Thread(
                target = self.configure_traffic_flow,
                args = (B,)
            )

            #P1.start()
            #P2.start()

            #P1.join()
            #P2.join()

        LOGGER.header('Start Test')
        P1 = Thread(
            target = self.start_mirror,
            args = (B,)
        )
        P2 = Thread(
            target = self.start_client,
            args = (A,)
        )

        ### ================================

        P3 = Thread(
            target = self.start_tail,
            args = (B,'mirror_vid100',)
        )
        P4 = Thread(
            target = self.start_tail,
            args = (A,'reference_vid100',)
        )

        ### ================================

        P1.start()
        P2.start()
        #P3.start()
        #P4.start()

        time.sleep(300)

        P1.join()
        P2.join()

        if not STATUS['isClientRunning'] and not STATUS['isMirrorRunning']:
            A.pkill('tail')
            B.pkill('tail')

        #P3.join()
        #P4.join()

        return 'PASSED'
