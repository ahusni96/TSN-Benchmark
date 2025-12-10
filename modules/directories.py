import os

HOMEDIR = f'/home/tsdace2/AMIRUL/tsn-script'

def create_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def get_homedir() -> str:
    return HOMEDIR

def get_logdir(platform: str, milestone: str) -> str:
    dir = f'{HOMEDIR}/logs/{platform.upper()}/{milestone.upper()}'
    create_directory(dir)
    return dir

def get_outdir(platform: str, milestone: str, chapter: str) -> str:
    dir = f'{HOMEDIR}/output/{platform.upper()}/{milestone.upper()}/{chapter}'
    create_directory(dir)
    return dir
