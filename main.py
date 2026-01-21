# System Imports
import argparse, glob, os, shutil, sys, time

# Case Imports
from cases.C01 import Case01
from cases.C02 import Case02
from cases.C03 import Case03
from cases.C04 import Case04
from cases.C05 import Case05
from cases.C06 import Case06
from cases.C09 import Case09
from cases.C10 import Case10

# Module Imports
import modules.rtcp
import modules.setup
import modules.shared as shared
import modules.directories as dir

from modules.options import Options
from modules.board import Board
from modules.runner import TestRunner

HOMEDIR = dir.get_homedir()

PARSER = argparse.ArgumentParser(
    description = 'Automated TSN UAT (v2)'
)
PARSER.add_argument(
    '--logdir',
    required = True,
    default = 'test'
)
PARSER.add_argument(
    '--platform',
    nargs = 2,
    required = False,
    choices = ['adln', 'adls', 'asl', 'ehl', 'rplp', 'rpls', 'tglh', 'tglu'],
    default = 'temp temp'
)
PARSER.add_argument(
    '--milestone',
    required = True,
    default = 'test'
)
PARSER.add_argument(
    '--os',
    nargs = 2,
    required = True,
    default = 'yocto yocto',
    choices = ['yocto', 'ubuntu']
)
PARSER.add_argument(
    '--ip',
    nargs = 2,
    required = True
)
PARSER.add_argument(
    '--user',
    required = False,
    default = 'root'
)
PARSER.add_argument(
    '--passwd',
    required = False,
    default = 'pass1234'
)
PARSER.add_argument(
    '--controller',
    nargs = 2,
    required = True,
    choices = [
        '811E1512', '811E2110', 'GPY115', 'GPY211', 'GPY215', 'DP83867E', 'I225',
        '811e1512', '811e2110', 'gpy115', 'gpy211', 'gpy215', 'dp83867e', 'i225'
    ]
)
PARSER.add_argument(
    '--interface',
    nargs = 2,
    required = True
)
PARSER.add_argument(
    '--dual',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--reboot',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--setup',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--rtcp',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--chapter',
    nargs = '*',
    choices = ['1','2','3','4','5','6','9','10'],
    required = False
)
PARSER.add_argument(
    '--flipped',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--workaround',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--run',
    required = False,
    default = 'default'
)


def main():
    options: Options = PARSER.parse_args(
        namespace = Options
    )

    # Clear temp folder
    shared.clear_folder(f'{HOMEDIR}/temp/')

    if not bool(options.flipped):
        A: Board = Board(
            side = 'A',
            ip = options.ip[0],
            platform = options.platform[0],
            milestone = options.milestone,
            controller = options.controller[0],
            interface = options.interface[0],
            os = options.os[0],
            user = options.user,
            passwd = options.passwd,
            dual = bool(options.dual)
        )

        B: Board = Board(
            side = 'B',
            ip = options.ip[1],
            platform = options.platform[1],
            milestone = options.milestone,
            controller = options.controller[1],
            interface = options.interface[1],
            os = options.os[1],
            user = options.user,
            passwd = options.passwd,
            dual = bool(options.dual)
        )
    else:
        B: Board = Board(
            side = 'B',
            ip = options.ip[0],
            platform = options.platform[0],
            milestone = options.milestone,
            controller = options.controller[0],
            interface = options.interface[0],
            os = options.os[0],
            user = options.user,
            passwd = options.passwd,
            dual = bool(options.dual)
        )

        A: Board = Board(
            side = 'A',
            ip = options.ip[1],
            platform = options.platform[1],
            milestone = options.milestone,
            controller = options.controller[1],
            interface = options.interface[1],
            os = options.os[1],
            user = options.user,
            passwd = options.passwd,
            dual = bool(options.dual)
        )

    runner = TestRunner(A, B, options.logdir, options.milestone)

    if bool(options.reboot):
        A.force_execute('shutdown -r now')
        B.force_execute('shutdown -r now')
    elif bool(options.setup):
        runner.set_chapter('setup')
        modules.setup.main(A, B, options.logdir, options.milestone)
    elif bool(options.rtcp):
        runner.set_chapter('rtcp')
        modules.rtcp.main(A, B, options.logdir, options.milestone)
    else:
        results: list[str] = []
        for item in options.chapter:
            match item.zfill(2):
                case '01':
                    runner.set_chapter('chapter-01')
                    results.append(Case01(runner).main())
                case '02':
                    runner.set_chapter('chapter-02')
                    results.append(Case02(runner).main())
                case '03':
                    runner.set_chapter('chapter-03')
                    results.append(Case03(runner).main())
                case '04':
                    runner.set_chapter('chapter-04')
                    results.append(Case04(runner).main())
                case '05':
                    runner.set_chapter('chapter-05')
                    results.append(Case05(runner).main())
                case '06':
                    runner.set_chapter('chapter-06')
                    results.append(Case06(runner).main())
                case '09':
                    runner.set_chapter('chapter-09')
                    results.append(Case09(runner).main())
                case '10':
                    runner.set_chapter('chapter-10')
                    results.append(Case10(runner).main())
                case _:
                    sys.exit(1)

        for r in range(len(options.chapter)):
            print(f'Case {options.chapter[r]}: {results[r]}')

if __name__ == '__main__':
    main()
