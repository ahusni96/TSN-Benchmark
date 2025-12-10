# System Imports
import csv, subprocess, time
from invoke.runners import Result

# Custom Imports
import modules.directories as dir
import modules.shared as shared
from modules.board import Board
from modules.logger import Log

HOMEDIR = dir.get_homedir()

def set_ingress_egress(board: Board) -> None:
    file = open(f'{HOMEDIR}/files/latency.csv', 'r')
    reader = csv.DictReader(file, strict = False)
    result = next(x for x in reader if x['controller'] == board.controller.upper() and x['mii'] == board.mii and x['speed'] == board.speed)
    board.ingress = result['ingress']
    board.egress = result['egress']

    if board.controller == 'i225':
        board.ingress = ''
        board.egress = ''


def show_eee(board: Board) -> None:
    try:
        res: Result = board.execute(f'ethtool --show-eee {board.interface}')
        LOGGER.info(res.stdout.strip())
        shared.save_output(OUTDIR, f'eee_{board.side}', res.stdout.strip())
    except:
        LOGGER.info('Unable to show EEE')


def set_eee(board: Board, status='off') -> None:
    try:
        res: Result = board.execute(f'ethtool --set-eee {board.interface} eee {status}')
        if res.return_code == 0:
            show_eee(board)
    except:
        LOGGER.info(f'Unable to set EEE to {status}')


def show_flow_control(board: Board) -> None:
    try:
        res: Result = board.execute(f'ethtool -a {board.interface}')
        LOGGER.info(res.stdout.strip())
        shared.save_output(OUTDIR, f'flow_control_{board.side}', res.stdout.strip())
    except:
        LOGGER.info(f'Unable to show flow control for {board.interface}')


def set_flow_control(board: Board, autoneg='off', rx='off', tx='off') -> None:
    try:
        res: Result = board.execute(f'ethtool -A {board.interface} autoneg {autoneg} rx {rx} tx {tx}')
        if res.return_code == 0:
            show_flow_control(board)
    except:
        LOGGER.info(f'Unable to set flow control for {board.interface}')


def show_timedatectl(board: Board) -> None:
    try:
        res: Result = board.execute(f'timedatectl')
        LOGGER.info(res.stdout.strip())
        shared.save_output(OUTDIR, f'timedatectl_{board.side}', res.stdout.strip())
    except:
        LOGGER.info('Unable to show timedate control')


def set_timedatectl(board: Board, ntp = 'false', local = 'false') -> None:
    try:
        res: Result = board.execute(f'timedatectl set-ntp {ntp} && timedatectl set-local-rtc {local}')
        if res.return_code == 0:
            show_timedatectl(board)
    except:
        LOGGER.info('Unable to set timedate control')


def show_mac(board: Board):
    try:
        res: Result = board.execute(f'ip link show dev {board.interface} | grep -i link/ether | xargs')
        mac = res.stdout.strip().split()[1]
        LOGGER.info(f'MAC Address {board.side}: {mac}')
    except Exception as e:
        LOGGER.info(f'Unable to fetch MAC Address from {board.side}-side')


def change_mac(board: Board, identifier: str, custom_addr: str = ''):
    if custom_addr != '':
        mac = custom_addr
    else:
        res: Result = board.execute(f'ip link show dev {board.interface} | grep -i link/ether')
        mac = res.stdout.strip().split()[1]

    temp = mac.split(':')
    temp[5] = identifier
    mac = ':'.join(temp)

    try:
        board.execute(f'ip link set dev {board.interface} down')
        board.execute(f'ip link set dev {board.interface} addr {mac}')
        board.execute(f'ip link set dev {board.interface} up')
        show_mac(board)
    except Exception as e:
        print(e)
        LOGGER.info(f'Unable to change MAC Address for {board.side}-side')


def show_ip(board: Board):
    try:
        res: Result = board.execute('ip -4 addr show ' + board.interface + ' | grep -oP "(?<=inet\\s)\\d+(\\.\\d+){3}"')
        LOGGER.info('IP Address: ' + res.stdout.strip())
    except:
        LOGGER.info(f'Unable to show IP Address from {board.side}-side')


def remove_ip(board: Board):
    try:
        res: Result = board.execute('ip -4 addr show ' + board.interface + ' | grep -oP "(?<=inet\\s)\\d+(\\.\\d+){3}"')
        ip_addr = res.stdout.strip()
        board.execute(f'ip addr del {ip_addr}/24 dev {board.interface}')
    except:
        return


def set_ip(board: Board, new_ip: str):
    try:
        res: Result = board.execute(f'ifconfig {board.interface} {new_ip}')
        if res.return_code == 0:
            show_ip(board)
    except:
        LOGGER.info(f'Unable to set IP Address for {board.side}-side')


def get_gPTP(board: Board):
    try:
        board.execute('cat /usr/share/iotg-tsn-ref-sw/common/gPTP.cfg')
    except:
        LOGGER.info(f'Unable to fetch gPTP.cfg from {board.side}-side')


def configure_gPTP(board: Board):
    try:
        if board.controller.lower() == 'i225':
            cmd: str = 'cp /usr/share/iotg-tsn-ref-sw/common/gPTP.cfg /home/root/gPTP.cfg'

            if board.os == 'ubuntu':
                cmd = cmd.replace('/home/root/gPTP.cfg', '/root/gPTP.cfg')

            res: Result = board.execute(cmd)
            if res.return_code == 0:
                LOGGER.info(f'gPTP.cfg has been configured for {board.interface}')
        else:
            subprocess.run(f'rm -rf {HOMEDIR}/temp/gPTP.cfg', shell=True)
            board.connection.get('/usr/share/iotg-tsn-ref-sw/common/gPTP.cfg', f'{HOMEDIR}/temp/gPTP.cfg')

            set_ingress_egress(board)

            with open(f'{HOMEDIR}/temp/gPTP.cfg', 'a') as w:
                w.write(f'\ningressLatency\t\t{board.ingress}\n')
                w.write(f'egressLatency\t\t{board.egress}')

            board.connection.put(f'{HOMEDIR}/temp/gPTP.cfg')

            # Check file exists
            res: Result = board.execute('ls | grep gPTP.cfg')
            if res.return_code == 0:
                LOGGER.info(f'gPTP.cfg has been configured for {board.controller}')
    except Exception as e:
        print(e)
        LOGGER.info(f'Unable to configure gPTP.cfg for {board.side}-side')


def move_files(board: Board):
    try:
        files = ['cyclictest', 'tsn-listener', 'tsn-talker', 'udp_tai', 'testptp']

        # Copy executables from host PC to remote system
        for item in files:
            board.connection.put(f'{HOMEDIR}/files/{item}')

        # Change file permission to enable file execution
        cmd = f'chmod +x '
        for item in files:
            cmd += f'{item} '

        board.execute(cmd.strip())

        # Check file exists
        res: Result = board.execute('ls | grep tsn- && ls | grep udp_tai')
        if res.return_code == 0:
            LOGGER.info('Executable files has been copied')
    except:
        LOGGER.info(f'Unable to copy files to {board.side}-side')


def get_BASE(board: Board):
    cmd = f'BASE=$(expr $(date +%s) + 5)000000000 && sleep 1 && echo "$BASE"'

    if board.controller.lower() == 'i225':
        cmd = f'BASE=$(date +%s%N) && sleep 1 && echo "$BASE"'

    try:
        res: Result = board.execute(cmd)
        return res.stdout.strip()
    except:
        LOGGER.info(f'Unable to calculate $BASE value from {board.side}-side')


def build_ref_sw(board: Board):
    cmd = 'cd /usr/share/iotg-tsn-ref-sw/ && ./build.sh && chmod +x *.sh json/*.sh'

    try:
        res: Result = board.execute(cmd)
        shared.save_output(OUTDIR, f'build_{board.side}', res.stdout.strip())

        if res.return_code == 0:
            LOGGER.info(f'Build completed for {board.side}-side')

    except Exception as e:
        print(e)
        LOGGER.info(f'TSN Ref SW build failed from {board.side}-side')


def set_eth_speed(board: Board, speed):
    cmd = f'ethtool -s {board.interface} speed {speed}'

    try:
        board.execute(cmd)
    except:
        LOGGER.info(f'Unable to set {board.interface} speed from {board.side}-side')


def kernel_workaround(board: Board):
    cmd = f'sysctl kernel.sched_rt_runtime_us=-1'

    try:
        board.execute(cmd)
    except:
        LOGGER.info(f'Unable to set kernel workaround')


def run_test(A: Board, B: Board, platform: str, milestone: str, workaround: bool = False) -> str:
    global OUTDIR, LOGDIR, LOGGER
    CHAPTER = 'chapter-1'
    OUTDIR = dir.get_outdir(platform, milestone, CHAPTER)
    LOGDIR = dir.get_logdir(platform, milestone)
    LOGGER = Log(CHAPTER, LOGDIR)

    A.set_logger(LOGGER)
    B.set_logger(LOGGER)

    LOGGER.info(f'###\tChapter 1 - Setup')

    LOGGER.header('Change MAC address')
    change_mac(A, '11', 'aa:00:aa:00:aa:00')
    LOGGER.info('')
    change_mac(B, '22', 'aa:00:aa:00:aa:00')
    time.sleep(1)


    LOGGER.header('Disable EEE')
    set_eee(A)
    LOGGER.info('')
    set_eee(B)
    time.sleep(1)


    LOGGER.header('Disable flow-control')
    set_flow_control(A)
    LOGGER.info('')
    set_flow_control(B)
    time.sleep(1)


    LOGGER.header('Disable NTP')
    set_timedatectl(A)
    LOGGER.info('')
    set_timedatectl(B)
    time.sleep(1)


    LOGGER.header('Configure gPTP.cfg')
    configure_gPTP(A)
    LOGGER.info('')
    configure_gPTP(B)
    time.sleep(1)


    LOGGER.header('Copy executable files')
    move_files(A)
    LOGGER.info('')
    move_files(B)
    time.sleep(1)


    LOGGER.header('Build IOTG-TSN-REF-SW')
    build_ref_sw(A)
    LOGGER.info('')
    build_ref_sw(B)
    time.sleep(1)

    if workaround:
        LOGGER.header('TEMP: Kernel Workaround')
        kernel_workaround(A)
        kernel_workaround(B)
        time.sleep(1)

    return 'PASSED'
