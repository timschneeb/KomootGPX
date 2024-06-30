import getpass


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


def sanitize_filename(value):
    for c in '\\/:*?"<>|':
        value = value.replace(c, '')
    return value
