from fabric import Result
from threading import Thread
import os, subprocess, sys, time

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner
from modules.sync import Sync
import modules.directories as dir
import modules.shared as shared

HOMEDIR = dir.get_homedir()

class Case03:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def check_queues(self, board: Board):
        try:
            res: Result = board.execute(f'ls /sys/class/net/{board.interface}/queues')
            LOGGER.info(res.stdout.replace('\n', ' '))
        except:
            LOGGER.error(f'Failed to check queues from {board.side}-side')

    def map_traffic(self, board: Board):
        cmd = f'tc qdisc replace dev {board.interface} handle 100: parent root mqprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 hw 0'

        if DUAL:
            cmd = f'tc qdisc replace dev {board.interface} handle 100: parent root mqprio num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 queues 1@0 1@1 hw 0'

        try:
            board.execute(cmd)
            res: Result = board.execute(f'tc -g class show dev {board.interface}')
            LOGGER.info(res.stdout.strip())
        except:
            LOGGER.error(f'Failed to map traffic from {board.side}-side')

    def set_traffic(self, board: Board):
        cmd = f'tc qdisc replace dev {board.interface} parent 100:2 cbs locredit -1350 hicredit 150 sendslope -900000 idleslope 100000 offload 1'

        if board.isFoxville():
            cmd = f'tc qdisc replace dev {board.interface} parent 100:1 cbs locredit -1350 hicredit 150 sendslope -900000 idleslope 100000 offload 1'

        try:
            board.execute(cmd)
            res: Result = board.execute(f'tc qdisc show dev {board.interface}')
            LOGGER.info(res.stdout.strip())
        except:
            LOGGER.error(f'Failed to set traffic from {board.side}-side')

    def start_talker(self, board: Board):
        cmd = f'./tsn-talker -d 01:AA:AA:AA:AA:AA -i {board.interface} -p 1 -s 1500'

        if board.isFoxville():
            cmd = f'./tsn-talker -d 01:AA:AA:AA:AA:AA -i {board.interface} -p 0 -s 1500'

        try:
            board.force_execute(cmd)
        except:
            LOGGER.error(f'Failed to start talker from {board.ip} ({board.side})')

    def start_listener(self, board: Board):
        try:
            board.force_execute(f'./tsn-listener -d 01:AA:AA:AA:AA:AA -i {board.interface} -s 1500')
        except:
            LOGGER.error(f'Failed to start listener from {board.ip} ({board.side})')

    def stop_tsn_program(self, boards):
        for item in boards:
            try:
                item.pkill('tsn-')
            except:
                item.logger.error('tsn-* process was not found')

    def verify_packets(self, board: Board):
        cmd = f'tc -s qdisc show dev {board.interface} | grep 100:2 -A3'

        if board.isFoxville():
            cmd = f'tc -s qdisc show dev {board.interface} | grep 100:1 -A3'

        try:
            res: Result = board.execute(cmd)
            LOGGER.info(res.stdout.strip('\n'))
        except:
            LOGGER.error('Failed to run verify packet command')

    def start_capture_packets(self, board: Board):
        try:
            board.execute(f'tcpdump -Q in -nvvvXXi {board.interface} --time-stamp-precision=nano -j adapter_unsynced -B 524288 -s 54 -w chapter_03.pcap')
        except:
            LOGGER.error('Failed to start tcpdump')

    def stop_capture_packets(self, board: Board):
        try:
            board.pkill('tcpdump')
            board.connection.get('chapter_03.pcap', f'{HOMEDIR}/temp/chapter_03.pcap')
        except:
            LOGGER.error(f'Failed to stop/validate tcpdump results')

    def validate_bit_rate(self):
        if os.path.exists(f'{HOMEDIR}/temp/chapter_03.pcap'):
            res = subprocess.run(f'capinfos {HOMEDIR}/temp/chapter_03.pcap | grep "Data bit rate:"', shell = True, capture_output = True, text = True)
            LOGGER.info(res.stdout.strip())
            shared.save_output(OUTDIR, 'capinfos', res.stdout.strip())
        else:
            LOGGER.info('*.pcap file was not found')

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

        LOGGER.info(f'###\tChapter 3 - Credit-Based Shaper')

        LOGGER.header('Start sync')
        PTP4L = Thread(
            target = SYNC.start_ptp4l,
            args = ()
        )

        PHC2SYS = Thread(
            target = SYNC.start_phc2sys,
            args = ()
        )

        PTP4L.start()
        time.sleep(30)

        PHC2SYS.start()
        time.sleep(60)

        LOGGER.header('Check queues')
        self.check_queues(A)

        LOGGER.header('Clear qdisc')
        A.clear_qdisk()
        B.clear_qdisk()

        LOGGER.header('Map traffic')
        self.map_traffic(A)

        LOGGER.header('Set traffic')
        self.set_traffic(A)

        LOGGER.header('Start TCPDUMP')
        TCPDUMP = Thread(
            target = self.start_capture_packets,
            args = (B,)
        )
        TCPDUMP.start()

        LOGGER.header('Start talker')
        T1 = Thread(
            target = self.start_talker,
            args = (A,)
        )
        T1.start()
        time.sleep(1)

        LOGGER.header('Start listener')
        T2 = Thread(
            target = self.start_listener,
            args = (B,)
        )
        T2.start()
        time.sleep(1)

        LOGGER.header('Verify packets')
        for i in range(6):
            time.sleep(10)
            self.verify_packets(A)

        LOGGER.header('Stop TCPDUMP')
        self.stop_capture_packets(B)

        LOGGER.header('Validate bit rate')
        self.validate_bit_rate()

        LOGGER.header('Stop sync')
        self.stop_tsn_program([A, B])
        T1.join()
        T2.join()
        A.pkill('iperf3')
        B.pkill('iperf3')

        SYNC.stop_sync()
        PHC2SYS.join()
        PTP4L.join()

        return 'PASSED'
