from fabric import Result
from invoke import Promise

import modules.shared as shared
from modules.board import Board
from modules.logger import Log

GPTP_DIR = "~/gPTP.cfg"

class Sync:
    def __init__(self, boards: list[Board], logger: Log, outdir: str) -> None:
        self.boards = boards
        self.logger = logger
        self.outdir = outdir


    def start_ptp4l(self):
        cmd = ['','']

        for i in range(len(self.boards)):
            cmd[i] = f'ptp4l -P2Hi {self.boards[i].interface} -f {GPTP_DIR} --step_threshold=1 -m'

            if self.boards[i].controller.lower() == 'i225' or self.boards[i].controller.lower() == 'i226':
                cmd[i] += ' --first_step_threshold=0.0'

        try:
            P1: Promise = self.boards[0].async_execute(cmd[0])
        except:
            self.logger.error(f'Failed to run ptp4l command on {self.boards[0].side}-side')

        try:
            P2: Promise = self.boards[1].async_execute(cmd[1])
        except:
            self.logger.error(f'Failed to run ptp4l command on {self.boards[1].side}-side')

        R1: Result = P1.join()
        R2: Result = P2.join()

        shared.save_output(self.outdir, 'ptp4l_A', R1.stdout.strip())
        shared.save_output(self.outdir, 'ptp4l_B', R2.stdout.strip())


    def start_phc2sys(self):
        cmd = ['','']

        for i in range(len(self.boards)):
            cmd[i] = f'phc2sys -s {self.boards[i].interface} -O 0 -c CLOCK_REALTIME --step_threshold=1 --transportSpecific=1 -w -m'

            if self.boards[i].controller.lower() == 'i225' or self.boards[i].controller.lower() == 'i226':
                cmd[i] += ' --first_step_threshold=0.0'

        try:
            P3: Promise = self.boards[0].async_execute(cmd[0])
        except:
            self.logger.error(f'Failed to run phc2sys command on {self.boards[0].side}-side')

        try:
            P4: Promise = self.boards[1].async_execute(cmd[1])
        except:
            self.logger.error(f'Failed to run phc2sys command on {self.boards[1].side}-side')

        R3: Result = P3.join()
        R4: Result = P4.join()

        shared.save_output(self.outdir, 'phc2sys_A', R3.stdout.strip())
        shared.save_output(self.outdir, 'phc2sys_B', R4.stdout.strip())


    def stop_sync(self):
        for item in self.boards:
            item.pkill('phc2sys')
            item.pkill('ptp4l')
