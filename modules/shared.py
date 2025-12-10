from modules.board import Board
import math

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
