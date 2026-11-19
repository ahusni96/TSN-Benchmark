### This script was used to setup yocto os in previous releases
### Status: Deprecated

from fabric import Result
import re

# Custom Imports
import modules.directories as dir
from modules.board import Board
from modules.logger import Log

HOMEDIR = dir.get_homedir()


def setup_connman(board: Board):
    res: Result = board.execute('[ -d "/etc/connman/" ] && echo "True" || echo "False"')
    exists = eval(res.stdout.strip())
    if not exists:
        try:
            board.execute('mkdir -p /etc/connman')
        except:
            LOGGER.error('Unable to create directory')

        with open(f'{HOMEDIR}/files/main.conf', 'r') as file:
            content = file.read()
            content = content.replace('<INTERFACE>', board.interface)

            with open(f'{HOMEDIR}/temp/main.conf', 'w') as final:
                final.write(content)
                final.close()

            file.close()

        try:
            board.connection.put(
                f'{HOMEDIR}/temp/main.conf',
                remote = '/etc/connman/'
            )
        except:
            LOGGER.error('Unable to copy file to SUT')


def config_kernel(board: Board):
    try:
        res: Result = board.execute('cat /proc/cmdline')
        output = res.stdout.strip()
    except:
        LOGGER.error('Unable to fetch kernel config information')

    try:
        res: Result = board.execute('printf "kernel.sched_rt_runtime_us=-1" >> /etc/sysctl.d/99-tsn.conf')
    except:
        LOGGER.error('Unable to set kernel.sched_rt_runtime_us value')

    try:
        temp = output.split()
        remove = [
            'rcupdate.rcu_cpu_stall_suppress=1',
            'rcu_nocb_poll',
            'iommu=pt',
            'rdt=!l3cat,!l2cat',
            'nohz=1-3',
            'nohz_full=1-3',
        ]

        isolcpus = -1
        rcu_nocbs = -1
        irqaffinity = -1

        for item in remove:
            if item in temp:
                temp.remove(item)

        for i in range(len(temp)):
            if re.search('isolcpus=', temp[i]) != None:
                isolcpus = i

            if re.search('rcu_nocbs=', temp[i]) != None:
                rcu_nocbs = i

            if re.search('irqaffinity=', temp[i]) != None:
                irqaffinity = i

        if isolcpus > -1:
            temp[isolcpus] = 'isolcpus=1-3'
            if board.dual:
                temp[isolcpus] = 'isolcpus=1-2'
        else:
            temp.append('isolcpus=1-3')
            if board.dual:
                temp[isolcpus] = 'isolcpus=1-2'

        if rcu_nocbs > -1:
            temp[rcu_nocbs] = 'rcu_nocbs=1-3'
            if board.dual:
                temp[rcu_nocbs] = 'rcu_nocbs=1-2'
        else:
            temp.append('rcu_nocbs=1-3')
            if board.dual:
                temp[rcu_nocbs] = 'rcu_nocbs=1-2'

        if irqaffinity > -1:
            temp[irqaffinity] = 'irqaffinity=0'
        else:
            temp.append('irqaffinity=0')

        with open(f'{HOMEDIR}/files/grub.cfg', 'r') as file:
            lines = file.read().replace('<CMDLINE>', ' '.join(temp).replace('BOOT_IMAGE=', ''))

            with open(f'{HOMEDIR}/temp/grub.cfg', 'w') as final:
                final.write(lines)
                final.close()

            file.close()
    except:
        LOGGER.error('Unable to configure grub.cfg')

    try:
        board.connection.put(
            f'{HOMEDIR}/temp/grub.cfg',
            remote='/boot/efi/EFI/BOOT/'
        )
    except:
        LOGGER.error('Failed to send grub.cfg to SUT')


def main(A: Board, B: Board, platform: str, milestone: str) -> int:
    global OUTDIR, LOGDIR, LOGGER
    CHAPTER = 'setup'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)

    if A.os == 'yocto':
        setup_connman(A)
        config_kernel(A)

    if B.os == 'yocto':
        setup_connman(B)
        config_kernel(B)

    A.force_execute('shutdown -r now')
    B.force_execute('shutdown -r now')
