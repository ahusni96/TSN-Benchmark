class Options:
    def __init__(self) -> None:
        self.chapter: list[str] = []
        self.platform: list[str] = ''
        self.milestone: str = ''
        self.os: list[str] = ''
        self.ip: list[str] = []
        self.user: str = ''
        self.passwd: str = ''
        self.controller: list[str] = []
        self.interface: list[str] = []
        self.dual: bool = False
        self.logdir: str = ''
        self.reboot: bool = False
        self.setup: bool = False
        self.rtcp: bool = False
        self.flipped: bool = False
