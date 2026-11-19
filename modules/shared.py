from fabric import Result
from modules.board import Board
import glob, math, os, re, shutil, sys, time

def duration(start, end):
    delta = end - start
    min = math.floor(delta / 60)
    min_str = f'{min} minute'

    if min > 1:
        min_str = min_str + 's'

    sec = round(delta % 60)
    sec_str = f'{sec} second'

    if sec > 1:
        sec_str = sec_str + 's'

    return f'\n-- Execution time: {min_str}, {sec_str}'

def save_output(dir: str, filename:str, text: str, permission: str = 'w'):
    try:
        with open(f'{dir}/{filename}.txt', permission) as f:
            f.write(text)
            f.close()
    except:
        return

def read_last(filename: str, lines: int):
    with open(filename) as f:
        data = f.readlines()

        if len(data) < lines:
            lines = len(data)

        return ''.join(data[-lines:])

def clear_folder(directory: str):
    if not directory.endswith('/'):
        directory += '/'

    files = glob.glob(f'{directory}*', recursive=True)
    for item in files:
        if os.path.isdir(item):
            shutil.rmtree(item)

        if os.path.isfile(item):
            os.remove(item)

def print_os_info(board: Board, side: str):
    result: Result = board.connection.run(
        f'dmidecode --string processor-version',
        hide = True
    )
    processor = result.stdout.strip()

    result: Result = board.connection.run(
        f'dmidecode --string bios-version',
        hide = True
    )
    bios = result.stdout.strip()

    result: Result = board.connection.run(
        f'dmidecode --string bios-release-date',
        hide = True
    )
    bios_date = result.stdout.strip()

    result: Result = board.connection.run(
        f'uname -r',
        hide = True
    )
    kernel_ver = result.stdout.strip()

    result: Result = board.connection.run(
        f'cat /etc/os-release | grep PRETTY_NAME',
        hide = True
    )
    pattern = r'\"(.*?)\"'
    match = re.search(pattern, result.stdout.strip())
    if match:
        os_version = match.group(1)
        board.logger.info(f'SIDE {side} :-')
        board.logger.info(f'Processor Version : {processor}\nBIOS Version : {bios}\nBIOS Release Date : {bios_date}')
        board.logger.info(f'Operating System : {os_version}\nKernel : {kernel_ver}')
    else:
        board.logger.info('OS info not found!')

def set_time(board: Board):
    try:
        localtime: time.struct_time = time.localtime()
        date_str: str = f'{str(localtime.tm_year).zfill(2)}-{str(localtime.tm_mon).zfill(2)}-{str(localtime.tm_mday).zfill(2)}'
        time_str: str = f'{str(localtime.tm_hour).zfill(2)}:{str(localtime.tm_min).zfill(2)}:{str(localtime.tm_sec).zfill(2)}'
        board.connection.run(f'timedatectl set-ntp false && timedatectl set-time "{date_str} {time_str}"')
    except:
        return
