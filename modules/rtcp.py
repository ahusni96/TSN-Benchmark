from fabric import Result
from datetime import timezone
from tabulate import tabulate
from threading import Thread

from modules.board import Board
from modules.logger import Log

import modules.directories as dir
import modules.shared as shared
import datetime, os, time


HOMEDIR: str = dir.get_homedir()

def get_rtcp_stat(board: Board):
    try:
        board.connection.get('/tmp/rtcp_statistic', 'temp')
    except:
        return

    with open('temp/rtcp_statistic') as file:
        lines = file.readlines()

def check_result(board: Board):
    with open(f'{OUTDIR}/{board.platform}_{set_device(board.controller)}_{board.side.upper()}-side.txt') as f:
        text = 'Calculating RTCP results...'
        lines = f.readlines()

        for i in range(len(lines)):
            if lines[i].strip() == text:
                HEADERS = lines[i + 2].strip().split()
                ROW1 = lines[i + 3].strip().split()
                ROW2 = lines[i + 4].strip().split()
                ROW3 = lines[i + 5].strip().split()

                table = tabulate([ROW1, ROW2, ROW3], HEADERS)
                LOGGER.info(table)
                LOGGER.info('')
                LOGGER.info(lines[i + 7].strip())
                LOGGER.info(lines[i + 8].strip())
                LOGGER.info(lines[i + 9].strip())
            i += 1

        f.close()

def set_packets(platform: str) -> str:
    match(platform):
        case 'ehl' | 'tglu' | 'tglh':
            return '100000'
        case 'adln':
            return '250000'
        case _:
            return '2400000'

def set_device(controller: str) -> str:
    match(controller.lower()):
        case 'i225' | 'i226':
            return 'i225'
        case _:
            return 'dwmac'

def msr(board: Board):
    if os.path.exists(f'{OUTDIR}/msr-tools-{board.side.lower()}'):
        os.remove(f'{OUTDIR}/msr-tools-{board.side.lower()}')

    if board.os == 'ubuntu':
        board.execute('apt update && apt install -y msr-tools')
    else:
        board.connection.put(f'{HOMEDIR}/files/msr-tools.zip', f'{board.home}/')
        board.execute(f'unzip {board.home}/msr-tools.zip')

        cmd: str = [
            'autoreconf --force --install --warnings=all',
            './configure $args "$@"',
            'make clean',
            'make',
            'make install'
        ]

        with board.connection.cd(f'{board.home}/msr-tools/'):
            for item in cmd:
                res: Result = board.execute(item)
                shared.save_output(OUTDIR, f'msr-tools-{board.side.lower()}', res.stdout.strip(), 'a')


def setup(board: Board, device: str = 'dwmac'):
    # device : {i225, dwmac}
    cmd = f'./rtcp.sh -p {board.platform.lower()} -h {set_device(board.controller)} -i {board.interface} -c rtcp1{board.side.lower()} -n {set_packets(board.platform)} -d 125000'

    if board.os == 'yocto':
        with board.connection.cd(f'{board.home}/rtcp-xdp/'):
            with board.connection.prefix(f'export PATH="{board.home}/msr-tools:$PATH"'):
                with open(f'{OUTDIR}/setup-{board.side}.txt', 'w') as file:
                    res: Result = board.execute(cmd)
                    file.write(res.stdout.strip())
                    res: Result = board.execute('./rtcp.sh -S')
                    file.write(f'\n{res.stdout.strip()}')
    else:
        with board.connection.cd(f'{board.home}/rtcp-xdp/'):
            with open(f'{OUTDIR}/setup-{board.side}.txt', 'w') as file:
                res: Result = board.execute(cmd)
                file.write(res.stdout.strip())
                res: Result = board.execute('./rtcp.sh -S')
                file.write(f'\n{res.stdout.strip()}')


def run(board: Board, device: str = 'dwmac'):
    if board.os == 'yocto':
        with board.connection.cd(f'{board.home}/rtcp-xdp/'):
            with board.connection.prefix(f'export PATH="{board.home}/msr-tools:$PATH"'):
                result: Result = board.execute('./rtcp.sh -R')
                with open(f'{OUTDIR}/{board.platform}_{set_device(board.controller)}_{board.side.upper()}-side.txt', 'w') as f:
                    f.write(result.stdout.strip())
                    f.close()
    else:
        with board.connection.cd(f'{board.home}/rtcp-xdp/'):
            result: Result = board.execute('./rtcp.sh -R')
            with open(f'{OUTDIR}/{board.platform}_{set_device(board.controller)}_{board.side.upper()}-side.txt', 'w') as f:
                f.write(result.stdout.strip())
                f.close()


#def timedatectl(boards: list [Board]):
#    dt = datetime.datetime.now()
#
#    A = boards[0]
#    B = boards[1]
#
#    cmd = f'timedatectl set-ntp false'
#    result: Result = A.execute(cmd)
#    result: Result = B.execute(cmd)
#
#    A.execute(f'timedatectl set-time \'{dt.strftime("%Y-%m-%d %H:%M:%S")}\'')
#    B.execute(f'timedatectl set-time \'{dt.strftime("%Y-%m-%d %H:%M:%S")}\'')
#
#    result: Result = A.execute('timedatectl')
#    LOGGER.info(result.stdout.strip())
#    result: Result = B.execute('timedatectl')
#    LOGGER.info(result.stdout.strip())


def main(A: Board, B: Board, platform: str, milestone: str) -> int:
    global OUTDIR, LOGDIR, LOGGER, DUAL
    CHAPTER = 'rtcp'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)
    DUAL = False
    SETUP = True

    A.set_logger(LOGGER)
    B.set_logger(LOGGER)

    setup_A = Thread(target = setup, args = (A, 'i225'))
    setup_B = Thread(target = setup, args = (B, 'i225'))

    run_A = Thread(target = run, args = (A, 'i225'))
    run_B = Thread(target = run, args = (B, 'i225'))

    if SETUP:
        #timedatectl([A, B])

        setup_A.start()
        setup_B.start()

        setup_A.join()
        setup_B.join()

        time.sleep(10)

    #start_time = time.time()

    run_B.start()
    time.sleep(1)
    run_A.start()

    run_A.join()
    run_B.join()

    #LOGGER.info(f'\nTOTAL DURATION: {shared.duration(start_time, time.time())}\n')

    A.pkill('phc2sys')
    B.pkill('phc2sys')

    A.pkill('ptp4l')
    B.pkill('ptp4l')

    A.execute('systemctl restart NetworkManager')
    B.execute('systemctl restart NetworkManager')

    # From output file find this line for the table -> Calculating RTCP results...
    # For passing:
    # - IFD Avg cannot be more than duration set
    # - RTCP Max cannot be more than IFD Avg

    #check_result(B)

