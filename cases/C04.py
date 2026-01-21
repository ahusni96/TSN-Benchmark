from invoke.runners import Result, Promise
from threading import Thread
import os, subprocess, time

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner
from modules.sync import Sync

import modules.directories as dir

HOMEDIR = dir.get_homedir()

isRunning = {
    'tcpdump': False,
    'server': False,
    'client': False,
}

class Case04:
    def __init__(self, runner: TestRunner):
        self.RUNNER = runner

    def setup_qdisc(self, board: Board):
        BASE = board.get_BASE()

        if board.platform.lower() == 'ehl':
            cmd = f'tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 8 map 0 1 2 3 4 5 6 7 7 7 7 7 7 7 7 7 queues 1@0 1@1 1@2 1@3 1@4 1@5 1@6 1@7 base-time {BASE} sched-entry S 03 5000000 sched-entry S 05 5000000 sched-entry S 09 5000000 sched-entry S 11 5000000 sched-entry S 21 2000000 sched-entry S 41 2000000 sched-entry S 81 2000000 flags 0x2 txtime-delay 0'
        elif board.controller.lower() == 'i225':
            cmd = f'tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry S 01 5000000 sched-entry S 02 5000000 sched-entry S 04 5000000 sched-entry S 08 5000000 flags 0x2 txtime-delay 0'
        else:
            cmd = f'tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry S 01 5000000 sched-entry S 03 5000000 sched-entry S 05 5000000 sched-entry S 09 5000000 flags 0x2 txtime-delay 0'

        if DUAL and board.controller.lower() == 'i225':
            cmd = f'tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 queues 1@0 1@1 base-time {BASE} sched-entry S 01 5000000 sched-entry S 02 5000000 flags 0x2 txtime-delay 0'

        try:
            board.force_execute(cmd)
        except:
            LOGGER.error(f'Failed to map traffic on {board.side}-side')


    def start_client(self, board: Board):
        try:
            board.force_execute('iperf3 -s -p 5100 > ~/5100.txt & iperf3 -s -p 5101 > ~/5101.txt & iperf3 -s -p 5102 > ~/5102.txt & iperf3 -s -p 5103 > ~/5103.txt')
        except:
            LOGGER.error(f'Failed to start iperf3 on {board.side}-side')


    def start_tcpdump(self, board: Board):
        try:
            if not isRunning['server']:
                return

            promise: Promise = board.async_execute(f'tcpdump -Q in -nvvvXXi {board.interface} --time-stamp-precision=nano -j adapter_unsynced -B 524288 -s 54 -w chp4_script.pcap -c 1000000')

            LOGGER.info('\nWaiting for TCPDUMP to finish...')

            isRunning['tcpdump'] = True
            promise.join()

            LOGGER.info('TCPDUMP Completed!')
            isRunning['tcpdump'] = False

            if isRunning['server']:
                LOGGER.info('Waiting for IPERF3 server to finish...')
                LOGGER.info('')
                LOGGER.info(f'Force closing iperf on A-side in 5 seconds')
                time.sleep(5)
                A.pkill('iperf3')

        except:
            LOGGER.error(f'Unable to complete tcpdump on {board.side}-side')


    def mount_net_prio(self, board: Board):
        try:
            board.execute('mkdir -p /sys/fs/cgroup/net_prio')
            board.execute('mount -t cgroup -onet_prio none /sys/fs/cgroup/net_prio')
        except:
            LOGGER.error(f'Unable to mount net_prio directory on {board.side}-side')


    def setup_net_prio(self, board: Board):
        if board.os == 'ubuntu':
            self.mount_net_prio(board)

        cmd = f'mkdir -p /sys/fs/cgroup/net_prio/grp1'
        cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp2'
        cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp3'
        cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp4'

        try:
            board.execute(cmd)
        except:
            LOGGER.error(f'Failed to create net_prio directory on {board.side}-side')

        cmd = f'echo "{board.interface} 1" > /sys/fs/cgroup/net_prio/grp1/net_prio.ifpriomap'
        cmd += f' && echo "{board.interface} 2" > /sys/fs/cgroup/net_prio/grp2/net_prio.ifpriomap'
        cmd += f' && echo "{board.interface} 3" > /sys/fs/cgroup/net_prio/grp3/net_prio.ifpriomap'
        cmd += f' && echo "{board.interface} 4" > /sys/fs/cgroup/net_prio/grp4/net_prio.ifpriomap'

        try:
            board.execute(cmd)
        except:
            LOGGER.error(f'Failed to use ifpriomap on {board.side}-side')


    def start_server(self, board: Board):
        try:
            cmd = f'iperf3 -u -l1000 -b0 -p 5100 -c {TARGET_IP} -t 150 >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp1/cgroup.procs'
            cmd += f' && iperf3 -u -l1000 -b0 -p 5101 -c {TARGET_IP} -t 150 >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp2/cgroup.procs'

            if not DUAL:
                cmd += f' && iperf3 -u -l1000 -b0 -p 5102 -c {TARGET_IP} -t 150 >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp3/cgroup.procs'

            if board.platform.lower() == 'ehl':
                cmd += f' && iperf3 -u -l1000 -b0 -p 5103 -c {TARGET_IP} -t 150 >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp4/cgroup.procs'

            promise: Promise = board.async_execute(cmd)
            isRunning['server'] = True

            result: Result = promise.join()
            LOGGER.info(result.stdout.strip())

            LOGGER.info('IPERF3 Completed!')
            isRunning['server'] = False

            if isRunning['tcpdump']:
                B.pkill('tcpdump')

            if result.return_code == 0:
                LOGGER.info('IPERF3 command has ended without error(s)')
            else:
                LOGGER.info('IPERF3 command has ended with error(s)')

        except:
            LOGGER.error(f'Failed to start iperf3 command on {board.side}-side')


    def download_pcap(self, board: Board):
        FILE = f'{HOMEDIR}/temp/chp4_script.pcap'

        try:
            if os.path.isfile(FILE):
                subprocess.run(f'rm -f {FILE}', shell=True)
            board.connection.get('chp4_script.pcap', FILE)

            if os.path.isfile(FILE):
                stats = os.stat(FILE)
                size = round(stats.st_size / (1024 * 1024))
                LOGGER.info(f'TCPDUMP filesize is {size} MB')
            else:
                LOGGER.error('TCPDUMP file does not exist in ' + FILE)
        except:
            LOGGER.error(f'Failed to get *.pcap file from target {board.side}')


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER, TARGET_IP, DUAL

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER

        TARGET_IP = '169.254.1.22'
        DUAL = False

        A.set_logger(LOGGER)
        B.set_logger(LOGGER)
        SYNC = Sync([A,B], LOGGER, OUTDIR)

        LOGGER.info(f'###\tChapter 4 - Time Aware Shaper (TAS)\n')

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
        time.sleep(10)

        PHC2SYS.start()
        time.sleep(50)

        LOGGER.header('Clear qdisc')
        A.clear_qdisk()
        B.clear_qdisk()

        time.sleep(1)

        LOGGER.header('Setup traffic')
        self.setup_qdisc(A)

        time.sleep(1)

        LOGGER.header('Setup net_prio')
        self.setup_net_prio(A)

        time.sleep(1)

        LOGGER.header('Set IP address')
        A.set_ip('169.254.1.11')
        LOGGER.info('')
        B.set_ip('169.254.1.22')

        time.sleep(1)

        LOGGER.header('Start IPERF3 client')
        CLIENT = Thread(
            target = self.start_client,
            args = (B,)
        )
        CLIENT.start()
        time.sleep(1)

        LOGGER.header('Start IPERF3 server')
        SERVER = Thread(
            target = self.start_server,
            args = (A,)
        )
        SERVER.start()
        time.sleep(30)

        LOGGER.header('Start TCPDUMP')
        TCPDUMP = Thread(
            target = self.start_tcpdump,
            args = (B,)
        )
        TCPDUMP.start()
        TCPDUMP.join()

        SERVER.join()
        CLIENT.join()

        LOGGER.header('Clear remaining processes')
        B.pkill('iperf3')

        LOGGER.header('Stop sync')
        SYNC.stop_sync()

        PHC2SYS.join()
        PTP4L.join()

        # LOGGER.header('Get *.pcap file')
        # download_pcap(B)

        return 'PASSED'
