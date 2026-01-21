from invoke.runners import Result, Promise
from threading import Thread
import sys, time

from modules.board import Board
from modules.logger import Log
from modules.sync import Sync

import modules.directories as dir
import modules.setup as setup
import modules.shared as shared

HOMEDIR = dir.get_homedir()


def enable_frame_preempt(board: Board, tool: str, kernel: str):
    try:
        match(tool):
            case 'ethtool':
                if float(kernel) > 6.14:
                    board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on tx-enabled on')
                else:
                    board.force_execute(f'ethtool --set-frame-preemption {board.interface} fp on')
                    res: Result = board.execute(f'ethtool --show-frame-preemption {board.interface}')
                    LOGGER.info(res.stdout.strip())
                time.sleep(10)
            case 'lldptool':
                board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on')
            case _:
                LOGGER.error(f'Invalid option for enabling FPE')
                return
    except:
        LOGGER.error('Failed to enable frame preemption')


def verify_frame_preempt(board: Board, kernel: str):
    try:
        if float(kernel) > 6.14:
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


def configure_old_queue(board: Board):
    cmd = f'BASE=$(date +%s%N) && tc qdisc add dev {board.interface} parent root handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time $BASE sched-entry S 0f 5000000 preempt 1100 flags 0x2'
    board.force_execute(cmd)
    res: Result = board.execute(f'tc qdisc show dev {board.interface}')
    LOGGER.info(res.stdout.strip())


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


def check_old_fpe_fragment(board: Board):
    try:
        res: Result = board.execute(f'ethtool -d {board.interface} | tail -n 13')
        shared.save_output(OUTDIR, f'FPE_fragment_{board.side}', res.stdout.strip())
        LOGGER.info(res.stdout.strip())
    except:
        LOGGER.error(f'Unable to check FPE fragment')


def check_fpe_fragment(board: Board):
    try:
        res: Result = board.execute(f"ethtool --include-statistics --show-mm {board.interface} | sed -n '/Statistics/,$p' | sed 1d")
        shared.save_output(OUTDIR, f'FPE_fragment_{board.side}', res.stdout.strip())
        LOGGER.info(res.stdout.strip())
    except:
        LOGGER.error(f'Unable to check FPE fragment')


def run_udp_tai(board: Board):
    try:
        cmd = f'./testing/udp_tai-Q0 -i {board.interface} -P 100000 -p 90 -d 60 -t 0 & '
        cmd += f'./testing/udp_tai-Q1 -i {board.interface} -P 100000 -p 90 -d 60 -t 1 & '
        cmd += f'./testing/udp_tai-Q2 -i {board.interface} -P 100000 -p 90 -d 60 -t 2 & '
        cmd += f'./testing/udp_tai-Q3 -i {board.interface} -P 100000 -p 90 -d 60 -t 3 & '
        cmd += f'sleep 10 ; pkill udp_tai'

        temp: Promise = board.async_execute(cmd)
        temp.join()
    except:
        LOGGER.error('Unable to start udp_tai')


# For PHY Controllers
#def legacy_case(kernel: float):
#
#    # Setup TAPRIO (Side-A)
#    BASE = '$(expr $(date +%s) + 5)000000000'
#    if kernel < 5.10:
#        globalA.force_execute(f'tc qdisc add dev {globalA.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry R 08 5000000 sched-entry H 00 5000000 sched-entry R 08 5000000 sched-entry H 00 5000000 flags 0x2 txtime-delay 0 fpe-qmask 0x07')
#    elif kernel <= 6.12 and kernel >= 5.10:
#        globalA.force_execute(f'tc qdisc add dev {globalA.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time {BASE} sched-entry R 08 5000000 sched-entry H 00 5000000 sched-entry R 08 5000000 sched-entry H 00 5000000 flags 0x2 txtime-delay 0 preempt 0111')
#    else:
#        return
#
#    # Verify TAPRIO (Side-A)
#    result: Result = globalA.execute(f'tc qdisc show dev {globalA.interface}')
#    LOGGER.info(result.stdout.strip())
#
#    # Enable multicast (Side-B)



# For 5.10 - 6.12 (ADL/RPL)
def i226_old():
    LOGGER.header('Set/Show frame preemption')
    enable_frame_preempt(globalA, 'ethtool', '6.12')
    enable_frame_preempt(globalB, 'ethtool', '6.12')

    LOGGER.header('Configure/Verify queue')
    configure_old_queue(globalA)

    LOGGER.header('Setup UDP_TAI')
    setup.setup_udp_tai(globalA, [68, 68, 1250, 1250])

    LOGGER.header('Check FPE fragments (before)')
    check_old_fpe_fragment(globalA)
    check_old_fpe_fragment(globalB)

    LOGGER.header('Run UDP_TAI')
    run_udp_tai(globalA)

    LOGGER.header('Check FPE fragments (after)')
    check_old_fpe_fragment(globalA)
    check_old_fpe_fragment(globalB)


# For 6.16 and above (PTL/WCL)
def case_current(tool: str = 'ethtool', config: str = 'taprio'):

    LOGGER.header(f'Enable FPE ({tool.upper()})')
    enable_frame_preempt(globalA, tool, '6.17')
    enable_frame_preempt(globalB, tool, '6.17')

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
    check_verfication_status(globalA, '6.17')
    check_verfication_status(globalB, '6.17')

    LOGGER.header('Configure TXQ PRIO')
    globalA.force_execute(f'ethtool --set-priv-flags {globalA.interface} reverse-tsn-txq-prio on')
    result: Result = globalA.execute(f'ethtool --show-priv-flags {globalA.interface}')
    LOGGER.info(result.stdout.strip())

    LOGGER.header('Setup UDP_TAI')
    setup.setup_udp_tai(globalA, [1250, 1250, 68, 68])

    LOGGER.header(f'Configure {config.upper()} queue')
    configure_queue(globalA, config)

    LOGGER.header('Check fragment counter (before)')
    check_fpe_fragment(globalA)
    check_fpe_fragment(globalB)

    LOGGER.header('Start udp_tai')
    run_udp_tai(globalA)

    LOGGER.header('Check fragment counter (after)')
    check_fpe_fragment(globalA)
    check_fpe_fragment(globalB)


def run_test(A: Board, B: Board, platform: str, milestone: str) -> str:
    global OUTDIR, LOGDIR, LOGGER, DUAL, globalA, globalB
    CHAPTER = 'chapter-6'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)
    DUAL = False

    globalA = A
    globalB = B

    A.set_logger(LOGGER)
    B.set_logger(LOGGER)

    LOGGER.info(f'###\tChapter 6 - Qbu Frame Preemption')

    LOGGER.header('Restart NetworkManager')
    A.force_execute('systemctl restart NetworkManager')
    B.force_execute('systemctl restart NetworkManager')

    LOGGER.header('Clear qdisc')
    A.clear_qdisk()
    B.clear_qdisk()

    # valid param values: [ethtool/lldptool] [taprio/mqprio]
    if A.controller.lower() == 'i225' and B.controller.lower() == 'i225':
        if A.kernel > 6.14 and B.kernel > 6.14:
            case_current('ethtool', 'taprio')
        else:
            i226_old()
    else:
        LOGGER.error('Mixed controllers not supported')

    return 'PASSED'
