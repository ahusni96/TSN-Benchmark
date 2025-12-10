from configparser import ConfigParser
from fabric import Result
from tabulate import tabulate
from threading import Thread
import argparse, datetime, os, sys, time

import modules.directories as dir
import modules.shared as shared
from modules.board import Board
from modules.logger import Log
from modules.sync import Sync

def configure_hw_clock(board: Board):
    cmd = 'pmc -u -b 0 -t 1 "SET GRANDMASTER_SETTINGS_NP clockClass 248 clockAccuracy 0xfe offsetScaledLogVariance 0xffff currentUtcOffset 37 leap61 0 leap59 0 currentUtcOffsetValid 1 ptpTimescale 1 timeTraceable 1 frequencyTraceable 0 timeSource 0xa0"'

    try:
        res: Result = board.execute(cmd)
        LOGGER.info(res.stdout.strip())
        shared.save_output(OUTDIR, f'configure_{board.side}', res.stdout.strip())
    except:
        LOGGER.error('Failed to configure hw_clock')

def print_logs():
    HEADERS = ['A-side', 'B-side']
    LINES = 50

    data_01 = [
        [
            shared.read_last(OUTDIR + '/ptp4l_A.txt', LINES),
            shared.read_last(OUTDIR + '/ptp4l_B.txt', LINES)
        ]
    ]

    data_02 = [
        [
            shared.read_last(OUTDIR + '/phc2sys_A.txt', LINES),
            shared.read_last(OUTDIR + '/phc2sys_B.txt', LINES)
        ]
    ]

    ptp4l = tabulate(data_01, HEADERS, 'simple_grid')
    phc2sys = tabulate(data_02, HEADERS, 'simple_grid')

    LOGGER.info('\n=== PTP4L ===\n')
    LOGGER.info(ptp4l)
    LOGGER.info('\n\n')
    LOGGER.info('=== PHC2SYS ===\n')
    LOGGER.info(phc2sys)

def run_test(A: Board, B: Board, platform: str, milestone: str) -> str:
    global OUTDIR, LOGDIR, LOGGER
    CHAPTER = 'chapter-2'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)

    A.set_logger(LOGGER)
    B.set_logger(LOGGER)
    SYNC = Sync([A,B], LOGGER, OUTDIR)

    LOGGER.info(f'###\tChapter 2 - gPTP and System Time Synchronization')

    LOGGER.header('Start ptp4l')
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

    LOGGER.header('Configure hardware clock')
    configure_hw_clock(A)
    LOGGER.info('')
    configure_hw_clock(B)

    LOGGER.header('Start phc2sys')
    PHC2SYS.start()
    time.sleep(50)

    LOGGER.header('Kill running processes')
    SYNC.stop_sync()
    PHC2SYS.join()
    PTP4L.join()

    print_logs()

    return 'PASSED'
