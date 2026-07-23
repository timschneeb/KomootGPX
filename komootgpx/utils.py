import getpass
import re
from datetime import datetime, timezone

class bcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def boolToColorStr(b):
    if b:
        return bcolor.OKGREEN + "true" + bcolor.ENDC
    else:
        return bcolor.FAIL + "false" + bcolor.ENDC

def print_error(text):
    print(bcolor.FAIL + text + bcolor.ENDC)

def print_success(text):
    print(bcolor.OKGREEN + text + bcolor.ENDC)

def print_warning(text):
    print(bcolor.WARNING + text + bcolor.ENDC)

def print_info(text):
    print(bcolor.OKBLUE + text + bcolor.ENDC)

def prompt(title):
    print()
    print(bcolor.BOLD + bcolor.HEADER + title + bcolor.ENDC)
    while True:
        selection = input(">")
        if len(selection) < 1:
            print(bcolor.FAIL + "Invalid input" + bcolor.ENDC)
            continue
        break
    print()
    return selection

def prompt_pass(title):
    print()
    print(bcolor.BOLD + bcolor.HEADER + title + bcolor.ENDC)
    while True:
        selection = getpass.getpass('Password: ')
        if len(selection) < 1:
            print(bcolor.FAIL + "Invalid input" + bcolor.ENDC)
            continue
        break
    print()
    return selection

RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
    '.', '..', ''
}

def sanitize_filename(value):
    # Strip illegal chars and control characters
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', value)

    # Strip trailing dots/spaces (strange Windows rule)
    value = value.rstrip('. ')

    name_part = value.split('.')[0].upper()
    if name_part in RESERVED_NAMES:
        value = '_' + value

    if not value:
        value = 'unnamed'

    return value

def shorten_path(path: str, max_len: int = 60) -> str:
    if len(path) <= max_len:
        return path
    # Keep start and end, replace middle with "..."
    keep = (max_len - 3) // 2
    return f"{path[:keep]}...{path[-keep:]}"

def parse_date_str(date_str):
    # Handles ISO 8601 with 'Z' suffix
    # python 3.11 has datetime.fromisoformat() with support of Z
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
