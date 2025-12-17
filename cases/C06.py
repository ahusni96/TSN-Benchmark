from invoke.runners import Result, Promise
from threading import Thread
import time

from modules.board import Board
from modules.logger import Log
from modules.sync import Sync

import modules.directories as dir
import modules.setup as setup
import modules.shared as shared

HOMEDIR = dir.get_homedir()

isRunning = {
    'server': False,
    'client': False,
}


def enable_frame_preempt(board: Board, tool: str):
    try:
        match(tool):
            case 'ethtool':
                board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on tx-enabled on')
                time.sleep(10)
            case 'lldptool':
                board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on')
            case _:
                LOGGER.error(f'Invalid option for enabling FPE')
                return
    except:
        LOGGER.error('Failed to enable frame preemption')


def verify_frame_preempt(board: Board):
    try:
        board.force_execute(f'ethtool --set-mm {board.interface} verify-enabled on')
    except:
        LOGGER.error('Failed to verify frame preempt')


def setup_lldptool(boards: list[Board]):
    try:
        LOGGER.header('Set LLDP status')
        for board in boards:
            board.force_execute(f'lldptool -L -i {board.interface} adminStatus=rxtx')

        time.sleep(10)

        LOGGER.header('Set TLV identifier')
        for board in boards:
            board.force_execute(f'lldptool -T -i {board.interface} -V addEthCaps enableTx=yes')
    except:
        LOGGER.error('Failed to setup with lldptool')


def check_verfication_status(board: Board):
    res: Result = board.execute(f'ethtool --show-mm {board.interface}')
    shared.save_output(OUTDIR, f'show_fpe_{board.side}', res.stdout.strip())
    LOGGER.info(res.stdout.strip())


#def add_qdisc(board: Board):
#    cmd = f'BASE=$(expr $(date +%s) + 5)000000000 && tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time $BASE sched-entry R 08 5000000 sched-entry H 00 5000000 sched-entry R 08 5000000 sched-entry H 00 5000000 flags 0x2 txtime-delay 0 preempt 0111'
#
#    if board.controller.lower() == 'i225' or board.controller.lower() == 'i226':
#        cmd = f'BASE=$(date +%s%N) && tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time $BASE sched-entry S 0f 5000000 preempt 1100 flags 0x2'
#
#    if DUAL and board.controller.lower() == 'i225' or board.controller.lower() == 'i226':
#        cmd = f'BASE=$(date +%s%N) && tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 queues 1@0 1@1 base-time $BASE sched-entry S 03 5000000 preempt 0010 flags 0x2'
#
#    try:
#        res: Result = board.execute(cmd)
#        shared.save_output(OUTDIR, f'qdisc_{board.side}', res.stdout.strip())
#        LOGGER.info(res.stdout.strip())
#    except:
#        LOGGER.error('Failed to add qdisc config')


#def verify_qdisc(board: Board):
#    try:
#        res: Result = board.execute('dmesg | grep FPE | grep -ioPm1 "(?<=pec = )[^ ]*"')
#        LOGGER.info(f'FPE: TxQ PEC = {res.stdout.strip()}')
#        shared.save_output(OUTDIR, f'dmesg_{board.side}', res.stdout.strip())
#    except:
#        LOGGER.error('Failed to verify qdisc config')


def configure_queue(board: Board, config: str):
    try:
        match(config):
            case 'taprio':
                cmd = f'tc qdisc add dev {board.interface} parent root handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time $(date +%s%N) sched-entry S 0F 5000000 flags 0x2 fp P P E E'
                board.force_execute(cmd)
                res: Result = board.execute(f'tc qdisc show dev {board.interface}')
                LOGGER.info(res.stdout.strip())
            case 'mqprio':
                cmd = f'tc qdisc add dev {board.interface} parent root handle 100 mqprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 fp P P E E'
                board.force_execute(cmd)
                res: Result = board.execute(f'tc qdisc show dev {board.interface}')
                LOGGER.info(res.stdout.strip())
            case _:
                LOGGER.error('Invalid option for configuring queue')
    except:
        LOGGER.error('Failed to configure queue')


def check_fpe_fragment(board: Board):
    try:
        res: Result = board.execute(f"ethtool --include-statistics --show-mm {board.interface} | sed -n '/Statistics/,$p' | sed 1d")
        shared.save_output(OUTDIR, f'FPE_fragment_{board.side}', res.stdout.strip())
        LOGGER.info(res.stdout.strip())
    except:
        LOGGER.error(f'Unabled to check FPE fragment')


def configure_cgroup(board: Board):
    try:
        board.force_execute('mkdir -p /sys/fs/cgroup/net_prio')
        board.force_execute('mount -t cgroup -onet_prio none /sys/fs/cgroup/net_prio')
    except:
        LOGGER.error(f'Unable to mount net_prio for {board.side}')

    cmd = f'mkdir -p /sys/fs/cgroup/net_prio/grp1'
    cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp2'
    cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp3'
    cmd += f' && mkdir -p /sys/fs/cgroup/net_prio/grp4'
    try:
        board.force_execute(cmd)
    except:
        LOGGER.error(f'Unable to create directory for net_prio for {board.side}')

    cmd = f'echo "{board.interface} 1" > /sys/fs/cgroup/net_prio/grp1/net_prio.ifpriomap'
    cmd += f' && echo "{board.interface} 2" > /sys/fs/cgroup/net_prio/grp2/net_prio.ifpriomap'
    cmd += f' && echo "{board.interface} 3" > /sys/fs/cgroup/net_prio/grp3/net_prio.ifpriomap'
    cmd += f' && echo "{board.interface} 4" > /sys/fs/cgroup/net_prio/grp4/net_prio.ifpriomap'
    try:
        board.force_execute(cmd)
    except:
        LOGGER.error(f'Unable to print inside net_prio from {board.side}')


#def start_server(board: Board):
#    cmd = 'iperf3 -s -p 5100 > ~/5100.txt & iperf3 -s -p 5101 > ~/5101.txt & iperf3 -s -p 5102 > ~/5102.txt & iperf3 -s -p 5103 > ~/5103.txt'
#
#    try:
#        board.force_execute(cmd)
#    except:
#        LOGGER.error(f'Unable to start server from {board.side}')


#def start_client(board: Board):
#    try:
#        cmd = f'iperf3 -u -l 1250 -b0 -p 5100 -c {TARGET_IP} >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp1/cgroup.procs '
#        cmd += f'&& iperf3 -u -l 1250 -b0 -p 5101 -c {TARGET_IP} >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp2/cgroup.procs '
#        cmd += f'&& iperf3 -u -l 68 -b0 -p 5102 -c {TARGET_IP} >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp3/cgroup.procs '
#        cmd += f'&& iperf3 -u -l 68 -b0 -p 5103 -c {TARGET_IP} >> /dev/null & echo $! > /sys/fs/cgroup/net_prio/grp4/cgroup.procs '
#
#        promise: Promise = board.async_execute(cmd)
#        result: Result = promise.join()
#        LOGGER.info('IPERF3 Completed!')
#
#        if result.return_code == 0:
#            LOGGER.info('IPERF3 command has ended without error(s)')
#        else:
#            LOGGER.info('IPERF3 command has ended with error(s)')
#    except:
#        LOGGER.error(f'Unable to start client from {board.side}')

def compile_udp_tai(board: Board, tx_buffers: list[int]):
    setup.setup_udp_tai(board, tx_buffers)

def run_udp_tai(board: Board):
    try:
        cmd = f'./udp_tai-Q0 -i {board.interface} -P 100000 -p 90 -d 60 -t 0 & '
        cmd += f'./udp_tai-Q1 -i {board.interface} -P 100000 -p 90 -d 60 -t 1 & '
        cmd += f'./udp_tai-Q2 -i {board.interface} -P 100000 -p 90 -d 60 -t 2 & '
        cmd += f'./udp_tai-Q3 -i {board.interface} -P 100000 -p 90 -d 60 -t 3 & '
        cmd += f'sleep 10 ; pkill udp_tai'

        temp: Promise = board.async_execute(cmd)
        temp.join()
    except:
        LOGGER.error('Unable to start udp_tai')


# For PHY Controllers
def legacy_case(kernel: float):

    # Setup TAPRIO (Side-A)
    BASE = '$(expr $(date +%s) + 5)000000000'
    if kernel < 5.10:
        globalA.force_execute(f'tc qdisc add dev {globalA.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry R 08 5000000 sched-entry H 00 5000000 sched-entry R 08 5000000 sched-entry H 00 5000000 flags 0x2 txtime-delay 0 fpe-qmask 0x07')
    elif kernel <= 6.12 and kernel >= 5.10:
        globalA.force_execute(f'tc qdisc add dev {globalA.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry R 08 5000000 sched-entry H 00 5000000 sched-entry R 08 5000000 sched-entry H 00 5000000 flags 0x2 txtime-delay 0 preempt 0111')
    else:
        return

    # Verify TAPRIO (Side-A)
    result: Result = globalA.execute(f'tc qdisc show dev {globalA.interface}')
    LOGGER.info(result.stdout.strip())

    # Enable multicast (Side-B)



# For 5.10 - 6.12 (ADL/RPL)
def i226_old():
    pass


# For 6.16 and above (PTL/WCL)
def case_current(tool: str = 'ethtool', config: str = 'taprio'):

    LOGGER.header(f'Enable FPE ({tool.upper()})')
    enable_frame_preempt(globalA, tool)
    enable_frame_preempt(globalB, tool)

    if tool == 'ethtool':
        LOGGER.header('Verify Frame Preempt')
        P1 = Thread(
            target = verify_frame_preempt,
            args = (globalA,)
        )
        P2 = Thread(
            target = verify_frame_preempt,
            args = (globalB,)
        )

        P1.start()
        P2.start()

        P2.join()
        P1.join()

    if tool == 'lldptool':
        setup_lldptool([globalA, globalB])

    time.sleep(10)

    LOGGER.header('Verify Frame Preempt')
    check_verfication_status(globalA)
    check_verfication_status(globalB)

    LOGGER.header('Configure TXQ PRIO')
    globalA.force_execute(f'ethtool --set-priv-flags {globalA.interface} reverse-tsn-txq-prio on')
    result: Result = globalA.execute(f'ethtool --show-priv-flags {globalA.interface}')
    LOGGER.info(result.stdout.strip())

    LOGGER.header('Set IP address')
    globalA.set_ip('192.168.1.11')
    LOGGER.info('')
    globalB.set_ip('192.168.1.22')

    LOGGER.header(f'Configure {config.upper()} queue')
    configure_queue(globalA, config)

    #LOGGER.header('Setup cgroup/net_prio folders')
    #configure_cgroup(globalA)

    LOGGER.header('Check fragment counter (before)')
    check_fpe_fragment(globalA)
    check_fpe_fragment(globalB)

    #LOGGER.header('Send traffic')
    #start_server(globalB)
    #time.sleep(5)
    #start_client(globalA)

    LOGGER.header('Start udp_tai')
    run_udp_tai(globalA)

    LOGGER.header('Check fragment counter (after)')
    check_fpe_fragment(globalA)
    check_fpe_fragment(globalB)


def run_test(A: Board, B: Board, platform: str, milestone: str) -> str:
    global OUTDIR, LOGDIR, LOGGER, DUAL, TARGET_IP, globalA, globalB
    CHAPTER = 'chapter-6'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)
    TARGET_IP = '192.168.1.22'
    DUAL = False

    globalA = A
    globalB = B

    A.set_logger(LOGGER)
    B.set_logger(LOGGER)
    SYNC = Sync([A,B], LOGGER, OUTDIR)

    LOGGER.info(f'###\tChapter 6 - Qbu Frame Preemption')

    LOGGER.header('Restart NetworkManager')
    A.force_execute('systemctl restart NetworkManager')
    B.force_execute('systemctl restart NetworkManager')

    #LOGGER.header('Start sync')
    PTP4L = Thread(
        target = SYNC.start_ptp4l,
        args = ()
    )
    #PTP4L.start()
    #time.sleep(10)

    PHC2SYS = Thread(
        target = SYNC.start_phc2sys,
        args = ()
    )
    #PHC2SYS.start()
    #time.sleep(50)

    LOGGER.header('Clear qdisc')
    A.clear_qdisk()
    B.clear_qdisk()

    # valid param values: [ethtool/lldptool] [taprio/mqprio]
    case_current('ethtool', 'taprio')

    #compile_udp_tai(A, [1250, 1250, 68, 68])

    # Split functions here

    #if A.controller.lower() == 'i225' or A.controller.lower() == 'i226':
    #    LOGGER.header('Enable Frame Preemption')
    #    enable_frame_preempt(A)
    #    time.sleep(1)

    #LOGGER.header('Clear qdisc')
    #A.clear_qdisk()
    #B.clear_qdisk()

    #LOGGER.header('Add qdisc')
    #add_qdisc(A)
    #time.sleep(1)

    #if A.controller.lower() != 'i225' or A.controller.lower() != 'i226':
    #    LOGGER.header('Show Frame Preemption')
    #    verify_qdisc(A)
    #    time.sleep(1)

    # End of split functions

    #LOGGER.header('Kill iperf3 processes')
    #A.pkill('iperf3')
    #B.pkill('iperf3')

    #LOGGER.header('Stop sync')
    #SYNC.stop_sync()
    #PHC2SYS.join()
    #PTP4L.join()

    return 'PASSED'
