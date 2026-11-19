# System Imports
import argparse, sys

# Case Imports
from cases.C01 import Case01
from cases.C02 import Case02
from cases.C03 import Case03
from cases.C04 import Case04
from cases.C05 import Case05
from cases.C06 import Case06

# Module Imports
import modules.shared as shared
import modules.directories as dir

from modules.options import Options
from modules.board import Board
from modules.runner import TestRunner
from modules.rtcp import RTCP_V2

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
    '--milestone',
    required = True,
    default = 'test'
)
PARSER.add_argument(
    '--os',
    nargs = 2,
    required = False,
    default = 'ubuntu ubuntu',
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
    default = '',
    choices = ['1ms', '125us'],
    required = False
)
PARSER.add_argument(
    '--chapter',
    nargs = '*',
    choices = ['1','2','3','4','5','6','9','10'],
    required = False
)
PARSER.add_argument(
    '--rerun',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--stress',
    action = 'store_true',
    required = False
)
PARSER.add_argument(
    '--test',
    action = 'store_true',
    required = False
)

def main():
    options: Options = PARSER.parse_args(
        namespace = Options
    )

    # Clear temp folder
    shared.clear_folder(f'{HOMEDIR}/temp/')

    A: Board = Board(
        side = 'A',
        ip = options.ip[0],
        milestone = options.milestone,
        os = options.os[0],
        user = options.user,
        passwd = options.passwd,
        dual = bool(options.dual)
    )

    B: Board = Board(
        side = 'B',
        ip = options.ip[1],
        milestone = options.milestone,
        os = options.os[1],
        user = options.user,
        passwd = options.passwd,
        dual = bool(options.dual)
    )

    runner = TestRunner(A, B, options.logdir, options.milestone, options.rerun, options.setup)

    if bool(options.reboot):
        A.force_execute('systemctl reboot -i')
        B.force_execute('systemctl reboot -i')
    elif bool(options.test):
        A.find_interface()
    elif str(options.rtcp) != '':
        runner.set_chapter(f'rtcp-{options.rtcp}')
        RTCP_V2(runner, str(options.rtcp), stress = options.stress).main()
        sys.exit(0)
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
                case _:
                    sys.exit(1)
            print(f'')

        for r in range(len(options.chapter)):
            print(f'Case {options.chapter[r]}: {results[r]}')

if __name__ == '__main__':
    main()
