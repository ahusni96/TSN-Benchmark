from fabric import Config, Connection, Result
from invoke import Promise
from paramiko import SSHConfig

from modules.logger import Log

class Board:
    def __init__(
            self,
            side: str,
            ip: str,
            platform: str,
            milestone: str,
            controller: str,
            interface: str,
            os: str,
            user: str = 'root',
            passwd: str = '',
            dual: bool = False):
        self.side: str = side
        self.ip: str = ip
        self.user: str = user
        self.passwd: str = passwd
        self.platform: str = platform
        self.milestone: str = milestone
        self.controller: str = controller
        self.speed: str = '1000'
        self.mii: str = 'SGMII'
        self.ingress: str = ''
        self.egress: str = ''
        self.interface: str = interface
        self.os: str = os
        self.logger: Log = None
        self.pty = True
        self.dual = dual
        self.config = Config(
            ssh_config = SSHConfig()
        )

        self.set_connection()
        self.set_home()
        self.find_kernel()

    def set_connection(self):
        self.connection = Connection(
            host = self.ip,
            user = self.user,
            config = self.config,
            connect_timeout = 120,
            connect_kwargs = {
                'password': self.passwd
            }
        )

    def set_logger(self, logger: Log):
        self.logger = logger

    def no_logger(self) -> bool:
        return self.logger is None

    def execute(self, cmd: str) -> Result:
        if not self.no_logger():
            self.logger.info(f'{self.side}-side:~$ {cmd}')

        return self.connection.run(
            cmd,
            hide = True
        )

    def async_execute(self, cmd: str) -> Promise:
        if not self.no_logger():
            self.logger.info(f'{self.side}-side:~$ {cmd}')

        return self.connection.run(
            cmd,
            asynchronous = True
        )

    def force_execute(self, cmd: str) -> None:
        if not self.no_logger():
            self.logger.info(f'{self.side}-side:~$ {cmd}')

        self.connection.run(
            cmd,
            disown = True
        )

    def pkill(self, process: str) -> None:
        self.force_execute(f'pkill {process}')


    def clear_qdisk(self) -> None:
        cmd = f'tc qdisc del dev {self.interface} root'
        try:
            self.force_execute(cmd)
        except:
            self.logger.error('Failed to clear qdisc config')

    def show_ip(self):
        try:
            res: Result = self.execute('ip -4 addr show ' + self.interface + ' | grep -oP "(?<=inet\s)\d+(\.\d+){3}"')
            self.logger.info('IP Address: ' + res.stdout.strip())
        except:
            self.logger.error(f'Unable to show IP Address from {self.side}-side')

    def remove_ip(self):
        try:
            res: Result = self.execute('ip -4 addr show ' + self.interface + ' | grep -oP "(?<=inet\s)\d+(\.\d+){3}"')
            ip_addr = res.stdout.strip()
            self.execute(f'ip addr del {ip_addr}/24 dev {self.interface}')
        except:
            return

    def set_ip(self, new_ip: str):
        try:
            res: Result = self.execute(f'ifconfig {self.interface} {new_ip}')
            if res.return_code == 0:
                self.show_ip()
        except:
            #res: Result = self.execute()
            self.logger.error(f'Unable to set IP Address for {self.side}-side')

    def get_BASE(self):
        cmd = f'BASE=$(expr $(date +%s) + 5)000000000 && sleep 1 && echo "$BASE"'

        if self.controller.lower() == 'i225' or self.controller.lower() == 'i226':
            cmd = f'BASE=$(date +%s%N) && sleep 1 && echo "$BASE"'

        try:
            res: Result = self.execute(cmd)
            return res.stdout.strip()
        except:
            self.logger.error(f'Unable to calculate $BASE value from {self.side}-side')

    def set_home(self):
        # value = True if condition else False
        self.home: str = f'/root' if self.os == 'ubuntu' else f'/home/root'

    def find_kernel(self):
        res: Result = self.connection.run(
            f'uname -r',
            hide = True
        )
        self.kernel: float = float(res.stdout.replace('rt-intel', ''))
