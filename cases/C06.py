from invoke.runners import Result, Promise
from threading import Thread
import sys, time

from modules.board import Board
from modules.logger import Log
from modules.runner import TestRunner
from modules.sync import Sync

import modules.directories as dir
import modules.setup as setup
import modules.shared as shared

HOMEDIR = dir.get_homedir()

class Case06:
    def __init__(self, runner: TestRunner):
        self.RUNNER: TestRunner = runner

    def enable_frame_preempt(self, board: Board, tool: str):
        try:
            match(tool):
                case 'ethtool':
                    if float(board.kernel) > 6.14:
                        board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on tx-enabled on')
                    else:
                        board.force_execute(f'ethtool --set-frame-preemption {board.interface} fp on')
                        res: Result = board.execute(f'ethtool --show-frame-preemption {board.interface}')
                        LOGGER.info(res.stdout.strip())
                case 'lldptool':
                    board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled on')
                    board.force_execute(f'lldpad -k')
                    time.sleep(5)
                    board.force_execute(f'lldpad -d')
                case _:
                    LOGGER.error(f'Invalid option for enabling FPE')
                    return
        except:
            LOGGER.error('Failed to enable frame preemption')


    def verify_frame_preempt(self, board: Board):
        try:
            if float(board.kernel) > 6.14:
                board.force_execute(f'ethtool --set-mm {board.interface} verify-enabled on')
        except:
            LOGGER.error('Failed to verify frame preempt')


    def setup_lldptool(self, board: Board):
        try:
            #LOGGER.header('Set LLDP status')
            result: Result = board.execute(f'lldptool -L -i {board.interface} adminStatus=rxtx')
            LOGGER.info(result.stdout.rstrip())
        except:
            LOGGER.error('Failed to setup with lldptool')

    def verify_lldptool(self, board: Board):
        try:
            #LOGGER.header('Set TLV identifier')
            result: Result = board.execute(f'lldptool -T -i {board.interface} -V addEthCaps enableTx=yes')
            LOGGER.info(result.stdout.rstrip())
            time.sleep(5)
        except:
            LOGGER.error('Failed to verify with lldptool')


    def check_verfication_status(self, board: Board) -> bool:
        #res: Result = board.execute(f'ethtool --show-mm {board.interface}')
        #shared.save_output(OUTDIR, f'show_fpe_{board.side}', res.stdout.strip())
        #LOGGER.info(res.stdout.strip())

        res: Result = board.execute(f'ethtool --show-mm {board.interface} | grep -i verification')
        LOGGER.info(res.stdout)
        tmp = res.stdout.replace('Verification status: ', '').replace('\n', '')
        if tmp == 'FAILED':
            return False
        else:
            return True


    def configure_old_queue(self, board: Board):
        if DUAL:
            cmd = f'BASE=$(date +%s%N) && tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 2 map 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 queues 1@0 1@1 base-time $BASE sched-entry S 03 5000000 preempt 0010 flags 0x2'
        else:
            cmd = f'BASE=$(date +%s%N) && tc qdisc add dev {board.interface} parent root stab overhead 24 handle 100 taprio num_tc 4 map 0 1 2 3 3 3 3 3 3 3 3 3 3 3 3 3 queues 1@0 1@1 1@2 1@3 base-time $BASE sched-entry S 0f 5000000 preempt 1100 flags 0x2'

        board.force_execute(cmd)
        res: Result = board.execute(f'tc qdisc show dev {board.interface}')
        LOGGER.info(res.stdout.strip())


    def configure_queue(self, board: Board, config: str):
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


    def check_old_fpe_fragment(self, board: Board):
        try:
            res: Result = board.execute(f'ethtool -d {board.interface} | tail -n 13')
            shared.save_output(OUTDIR, f'FPE_fragment_{board.side}', res.stdout.strip())
            LOGGER.info(res.stdout.strip())
        except:
            LOGGER.error(f'Unable to check FPE fragment')


    def check_fpe_fragment(self, board: Board):
        try:
            res: Result = board.execute(f"ethtool --include-statistics --show-mm {board.interface} | sed -n '/Statistics/,$p' | sed 1d")
            shared.save_output(OUTDIR, f'FPE_fragment_{board.side}', res.stdout.strip())
            LOGGER.info(res.stdout.rstrip())
        except:
            LOGGER.error(f'Unable to check FPE fragment')


    def run_udp_tai(self, board: Board):
        try:
            cmd = f'./testing/udp_tai-Q0 -i {board.interface} -P 100000 -p 90 -d 60 -t 0 & '
            cmd += f'./testing/udp_tai-Q1 -i {board.interface} -P 100000 -p 90 -d 60 -t 1 & '
            cmd += f'./testing/udp_tai-Q2 -i {board.interface} -P 100000 -p 90 -d 60 -t 2 & '
            cmd += f'./testing/udp_tai-Q3 -i {board.interface} -P 100000 -p 90 -d 60 -t 3 & '
            cmd += f'sleep 5 ; pkill udp_tai'

            temp: Promise = board.async_execute(cmd)
            temp.join()
        except:
            LOGGER.error('Unable to start udp_tai')

    def reset_mm(self, board: Board):
        try:
            board.force_execute(f'ethtool --set-mm {board.interface} pmac-enabled off tx-enabled off verify-enabled off')
        except:
            LOGGER.error('Unable to reset ethtool mm config')


    # For 5.10 - 6.12 (ADL/RPL)
    def i226_old(self):
        LOGGER.header('Set/Show frame preemption')
        self.enable_frame_preempt(A, 'ethtool')
        self.enable_frame_preempt(B, 'ethtool')

        LOGGER.header('Configure/Verify queue')
        self.configure_old_queue(A)

        LOGGER.header('Setup UDP_TAI')
        setup.setup_udp_tai(A, [68, 68, 1250, 1250])

        LOGGER.header('Check FPE fragments (before)')
        self.check_old_fpe_fragment(A)
        self.check_old_fpe_fragment(B)

        LOGGER.header('Run UDP_TAI')
        self.run_udp_tai(A)

        LOGGER.header('Check FPE fragments (after)')
        self.check_old_fpe_fragment(A)
        self.check_old_fpe_fragment(B)


    # For 6.16 and above (PTL/WCL)
    def case_current(self, tool: str = 'ethtool', config: str = 'taprio'):
        if not RERUN:
            LOGGER.header(f'Reset MM Config')
            self.reset_mm(A)
            self.reset_mm(B)

            LOGGER.header(f'Enable FPE ({tool.upper()})')
            self.enable_frame_preempt(A, tool)
            self.enable_frame_preempt(B, tool)

            time.sleep(5)

            if tool == 'ethtool':
                LOGGER.header('Verify Frame Preempt')
                P1 = Thread(
                    target = self.verify_frame_preempt,
                    args = (A,)
                )
                P2 = Thread(
                    target = self.verify_frame_preempt,
                    args = (B,)
                )

                P1.start()
                P2.start()

                P2.join()
                P1.join()


            if tool == 'lldptool':
                LOGGER.header('Set LLDP status')
                self.setup_lldptool(A)
                self.setup_lldptool(B)

                LOGGER.header('Set TLV identifier')
                P1 = Thread(
                    target = self.verify_lldptool,
                    args = (A,)
                )

                P2 = Thread(
                    target = self.verify_lldptool,
                    args = (B,)
                )

                P1.start()
                P2.start()

                P1.join()
                P2.join()

            time.sleep(5)

        LOGGER.header('Verify Frame Preempt')
        tmp: list[bool] = []
        tmp.append(self.check_verfication_status(A))
        tmp.append(self.check_verfication_status(B))

        if not tmp[0] or not tmp[1]:
            sys.exit(1)


        LOGGER.header('Configure TXQ PRIO')
        if not RERUN:
            A.force_execute(f'ethtool --set-priv-flags {A.interface} reverse-tsn-txq-prio on')
        result: Result = A.execute(f'ethtool --show-priv-flags {A.interface}')
        LOGGER.info(result.stdout.strip())

        if not RERUN:
            LOGGER.header('Setup UDP_TAI')
            setup.setup_udp_tai(A, [1250, 1250, 68, 68])

        LOGGER.header(f'Configure {config.upper()} queue')
        self.configure_queue(A, config)

        LOGGER.header('Check fragment counter (before)')
        self.check_fpe_fragment(A)
        self.check_fpe_fragment(B)

        if not RERUN:
            LOGGER.header('Set multicast for B side')
            B.force_execute(f'ip link set dev {B.interface} multicast on')
            B.force_execute(f'ip link set dev {B.interface} allmulticast on')

        time.sleep(10)

        LOGGER.header('Start udp_tai')
        self.run_udp_tai(A)

        LOGGER.header('Check fragment counter (after)')
        self.check_fpe_fragment(A)
        self.check_fpe_fragment(B)


    def main(self) -> str:
        global A, B, OUTDIR, LOGDIR, LOGGER, DUAL, RERUN, OLD

        A = self.RUNNER.A
        B = self.RUNNER.B
        OUTDIR = self.RUNNER.OUTDIR
        LOGDIR = self.RUNNER.LOGDIR
        LOGGER = self.RUNNER.LOGGER
        RERUN = False #self.RUNNER.RERUN
        DUAL = False
        OLD = False

        A.set_logger(LOGGER)
        B.set_logger(LOGGER)

        LOGGER.info(f'###\tChapter 6 - Qbu Frame Preemption')

        #LOGGER.header('Restart Network Interface')
        #A.restart_interface()
        #B.restart_interface()

        LOGGER.header('Clear qdisc')
        A.clear_qdisk()
        B.clear_qdisk()

        # valid param values: [ethtool/lldptool] [taprio/mqprio]
        if A.controller.lower() == 'i225' and B.controller.lower() == 'i225':
            if A.kernel > 6.14 and B.kernel > 6.14 and not OLD:
                self.case_current('ethtool', 'taprio')
            else:
                self.i226_old()
        else:
            LOGGER.error('Mixed controllers not supported')

        return 'PASSED'
