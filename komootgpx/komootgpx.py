import getopt
import os
import sys

from colorama import init

from .api import *
from .gpxcompiler import *
from .utils import *

init()
interactive_info_shown = False


def usage():
    print(bcolor.HEADER + bcolor.BOLD + 'komootgpx.py [options]' + bcolor.ENDC)
    print(bcolor.OKBLUE + '[Authentication]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-m', '--mail=mail_address', 'Login using specified email address'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-p', '--pass=password',
                                             'Use provided password and skip interactive prompt'))
    print(bcolor.OKBLUE + '[Tours]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-l', '--list-tours', 'List all tours of the logged in user'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-d', '--make-gpx=tour_id', 'Download tour as GPX'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-a', '--make-all', 'Download all tours'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-D', '--add-date', 'Add date to file name'))
    print(bcolor.OKBLUE + '[Filters]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-f', '--filter=type', 'Filter by track type (either "planned" or '
                                                                    '"recorded")'))
    print(bcolor.OKBLUE + '[Generator]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-o', '--output', 'Output directory (default: working directory)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-e', '--no-poi', 'Do not include highlights as POIs'))


def notify_interactive():
    global interactive_info_shown
    interactive_info_shown = True
    if interactive_info_shown:
        print("Interactive mode. Use '--help' for usage details.")


def make_gpx(tour_id, api, output_dir, no_poi, add_date):
    tour = api.fetch_tour(str(tour_id))
    gpx = GpxCompiler(tour, api, no_poi)

    # Example date: 2022-01-02T12:26:41.795+01:00
    # :10 extracts "2022-01-02" from this.
    date_str = tour['date'][:10]+'_' if add_date else ''

    path = f"{output_dir}/{date_str}{sanitize_filename(tour['name'])}-{tour_id}.gpx"
    f = open(path, "w", encoding="utf-8")
    f.write(gpx.generate())
    f.close()

    print_success(f"GPX file written to '{path}'")


def main(argv):
    tour_selection = ''
    mail = ''
    pwd = ''
    print_tours = False
    no_poi = False
    add_date = False
    typeFilter = "all"
    output_dir = os.getcwd()

    try:
        opts, args = getopt.getopt(argv, "ahleDo:d:m:p:f:", ["add-date", "list-tours", "make-gpx=", "mail=",
                                                        "pass=", "filter=", "no-poi", "output=", "make-all"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()

        elif opt in "--filter":
            typeFilter = "tour_" + str(arg)

        elif opt in ("-l", "--list-tours"):
            print_tours = True

        elif opt in ("-e", "--no-poi"):
            no_poi = True

        elif opt in ("-D", "--add-date"):
            add_date = True

        elif opt in ("-d", "--make-gpx"):
            tour_selection = str(arg)

        elif opt in ("-m", "--mail"):
            mail = str(arg)

        elif opt in ("-p", "--pass"):
            pwd = str(arg)

        elif opt in ("-o", "--output"):
            output_dir = str(arg)

        elif opt in ("-a", "--make-all"):
            tour_selection = "all"

    if mail == "":
        notify_interactive()
        mail = prompt("Enter your mail address (komoot.de)")

    if pwd == "":
        notify_interactive()
        pwd = prompt_pass("Enter your password (input hidden)")

    api = KomootApi()
    api.login(mail, pwd)

    if tour_selection == "":
        notify_interactive()
        api.print_tours(typeFilter)
        tour_selection = prompt("Enter a tour id to download")

    if print_tours:
        api.print_tours(typeFilter)
        exit(0)

    tours = api.fetch_tours(typeFilter)

    if tour_selection != "all" and int(tour_selection) not in tours:
        print_error("Unknown tour id selected. These are all available tours on your profile:")
        api.print_tours(typeFilter)
        exit(0)

    if tour_selection == "all":
        for x in tours:
            make_gpx(x, api, output_dir, no_poi, add_date)
    else:
        make_gpx(tour_selection, api, output_dir, no_poi, add_date)
    print()


def entrypoint():
    try:
        return main(sys.argv[1:])
    except KeyboardInterrupt:
        print()
        print_error("Aborted by user")
        exit(1)