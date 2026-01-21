from modules.board import Board
from modules.logger import Log

import modules.directories as dir

class TestRunner:
    def __init__(self, a: Board, b: Board, platform: str, milestone: str):
        self.A: Board = a
        self.B: Board = b
        self.PLATFORM: str = platform
        self.MILESTONE: str = milestone
        self.LOGDIR: str = dir.get_logdir(platform, milestone)

    def set_chapter(self, chapter: str):
        self.CHAPTER = chapter
        self.OUTDIR: str = dir.get_outdir(self.PLATFORM, self.MILESTONE, self.CHAPTER)
        self.LOGGER: Log = Log(self.CHAPTER, self.LOGDIR)
        self.A.set_logger(self.LOGGER)
        self.B.set_logger(self.LOGGER)
