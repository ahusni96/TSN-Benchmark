from fabric import Result
from tabulate import tabulate
from threading import Thread
import math, time

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner
from modules.sync import Sync

import modules.directories as dir
import modules.shared as shared

HOMEDIR = dir.get_homedir()

class Case05:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def add_qdisc(self, board: Board):
        cmd = f'tc qdisc add dev {board.interface} handle 8001: parent root mqprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 hw 0'

        if board.platform.lower() == 'ehl' and board.controller.lower() != 'i225':
            cmd = f'tc qdisc add dev {board.interface} handle 8001: parent root mqprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 2@2 1@4 hw 0'

        if DUAL:
            cmd = f'tc qdisc add dev {board.interface} handle 8001: parent root mqprio num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 queues 1@0 1@1 hw 0'

        try:
            board.execute(cmd)
        except Exception as e:
            print(e)
            LOGGER.error(f'Failed to add qdisc for side-{board.side}')


    def replace_qdisc(self, board: Board):
        cmd = f'tc qdisc replace dev {board.interface} parent 8001:4 etf offload clockid CLOCK_TAI delta 500000'

        if board.platform.lower() == 'ehl' and board.controller.lower() != 'i225':
            cmd = f'tc qdisc replace dev {board.interface} parent 8001:5 etf offload clockid CLOCK_TAI delta 500000'

        if DUAL:
            cmd = f'tc qdisc replace dev {board.interface} parent 8001:2 etf offload clockid CLOCK_TAI delta 500000'

        try:
            board.execute(cmd)
        except Exception as e:
            print(e)
            LOGGER.error(f'Failed to replace qdisc for side-{board.side}')


    def show_qdisc(self, board: Board):
        try:
            res: Result = board.execute(f'tc qdisc show dev {board.interface}')
            LOGGER.info(res.stdout.strip())
            shared.save_output(OUTDIR, f'qdisc_{board.side}', res.stdout.strip())
        except:
            LOGGER.error('Failed to show qdisc config')


    def start_udp(self, board: Board):
        try:
            cmd = f'./udp_tai -c 3 -i {board.interface} -P 1000000 -p 90 -d 600000'

            if DUAL:
                cmd = f'./udp_tai -i {board.interface} -P 1000000 -p 90 -d 600000'

            board.force_execute(cmd)
        except:
            LOGGER.error('Unable to start udp_tai')


    def stop_udp(self, board: Board):
        board.pkill('udp_tai')


    def start_tcpdump(self, board: Board):
        try:
            res: Result = board.execute(f'tcpdump -Q in -ttt -ni {board.interface} --time-stamp-precision=nano -j adapter_unsynced port 7788 -c 100000')
            shared.save_output(OUTDIR, f'tcpdump_{board.side}', res.stdout.strip())
        except:
            LOGGER.error('Unable to start tcpdump')


    def validate_results(self):
        # EXPECTED RESULT: time difference around +/-500ns
        # 1 nanosecond = 1 / 10^9 second

        directory = f'{OUTDIR}/tcpdump_B.txt'

        try:
            with open(directory) as file:
                count = 0
                total = 0
                lines = file.readlines()

                for i in range(1, len(lines)):
                    if i == len(lines) - 1:
                        break

                    val_1 = (lines[i].split()[0]).split(':')[2]
                    val_2 = (lines[i + 1].split()[0]).split(':')[2]

                    time_1 = float(val_1)
                    time_2 = float(val_2)

                    nanoseconds = lambda a: math.floor(a * math.pow(10, 9))

                    diff = nanoseconds(round((time_2 - time_1), 9))

                    if diff < -500 or diff > 500:
                        count += 1

                    total += 1

                failed_percent = (count / total) * 100

                self.print_logs()

                LOGGER.info(f'Total Lines: {len(lines)}\nPassed (+/-500ns): {100 - round(failed_percent, 2)}%\nFailed: {round(failed_percent, 2)}%')
        except:
            LOGGER.error('Failed to validate results')


    def print_logs(self):
        HEADERS = ['B-side']
        LINES = 50

        data = [
            [shared.read_last(f'{OUTDIR}/tcpdump_B.txt', LINES).strip()]
        ]

        tcpdump = tabulate(data, HEADERS, 'simple_grid')

        LOGGER.info(tcpdump)
        LOGGER.info('\n')


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
        SYNC = Sync([A,B], LOGGER, OUTDIR)

        LOGGER.info(f'###\tChapter 5 - Time-Based Scheduling (TBS)')

        LOGGER.header('Start sync')
        PTP4L = Thread(
            target = SYNC.start_ptp4l,
            args = ()
        )
        PTP4L.start()
        time.sleep(5)

        PHC2SYS = Thread(
            target = SYNC.start_phc2sys,
            args = ()
        )
        PHC2SYS.start()
        time.sleep(60)

        LOGGER.header('Clear qdisc')
        A.clear_qdisk()
        B.clear_qdisk()

        LOGGER.header('Add qdisc')
        self.add_qdisc(A)
        time.sleep(1)

        LOGGER.header('Replace qdisc')
        self.replace_qdisc(A)
        time.sleep(1)

        LOGGER.header('Show qdisc')
        self.show_qdisc(A)
        time.sleep(1)

        LOGGER.header('Start UDP_TAI')
        self.start_udp(A)
        time.sleep(10)

        LOGGER.header('Run TCPDUMP')
        T1 = Thread(
            target = self.start_tcpdump,
            args = (B,)
        )
        T1.start()
        T1.join()

        LOGGER.header('Stop UDP_TAI')
        self.stop_udp(A)

        LOGGER.header('Stop sync')
        SYNC.stop_sync()
        PHC2SYS.join()
        PTP4L.join()

        LOGGER.header('Validate results')
        self.validate_results()

        return 'PASSED'
