import os
import sys
import datetime

from colorama import init

from .api import *
from .gpxcompiler import *
from .utils import *

import argparse

init()
interactive_info_shown = False


def usage():
    print(bcolor.HEADER + bcolor.BOLD + 'komootgpx.py [options]' + bcolor.ENDC)

    print('\n' + bcolor.OKBLUE + '[Authentication]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-m', '--mail=mail_address', 'Login using specified email address'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-p', '--pass=password', 'Use provided password and skip interactive prompt'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-n', '--anonymous', 'Skip authentication, no interactive prompt, valid only with -d'))

    print('\n' + bcolor.OKBLUE + '[Tours]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-l', '--list-tours', 'List all tours of the logged in user'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-d', '--make-gpx=tour_id', 'Download tour as GPX'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-a', '--make-all', 'Download all tours'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-s', '--skip-existing', 'Do not download and save GPX if the file already exists, ignored with -d'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-I', '--id-filename', 'Use only tour id for filename (no title)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-D', '--add-date', 'Add date to file name'))
    print('\t{:<34s} {:<10s}'.format('--max-title-length=num', 'Crop title used in filename to given length (default: -1 = no limit)'))

    print('\n' + bcolor.OKBLUE + '[Filters]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-f', '--filter=type', 'Filter by track type (either "planned" or "recorded")'))
    print('\t{:<34s} {:<10s}'.format('--start-date=YYYY-MM-DD', 'Filter tours on or after specified date (optional)'))
    print('\t{:<34s} {:<10s}'.format('--end-date=YYYY-MM-DD', 'Filter tours on or before specified date (optional)'))

    print('\n' + bcolor.OKBLUE + '[Generator]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-o', '--output', 'Output directory (default: working directory)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-e', '--no-poi', 'Do not include highlights as POIs'))
    print('\t{:<34s} {:<10s}'.format('--max-desc-length=count', 'Limit description length in characters (default: -1 = no limit)'))


def is_tour_in_date_range(tour, start_date, end_date):
    """Check if a tour falls within the specified date range."""
    if 'date' not in tour:
        return True  # If tour has no date info, include it

    tour_date_str = tour['date'][:10]  # Extract YYYY-MM-DD
    tour_date = datetime.strptime(tour_date_str, "%Y-%m-%d").date()

    # If only start_date is provided, include all tours on or after start_date
    if start_date and not end_date and tour_date < start_date:
        return False

    # If only end_date is provided, include all tours on or before end_date
    if end_date and not start_date and tour_date > end_date:
        return False

    # If both dates are provided, ensure tour is within range
    if start_date and end_date and (tour_date < start_date or tour_date > end_date):
        return False

    return True

def date_filter(tours, start_date, end_date):
    # Filter tours by date if specified
    if not start_date and not end_date:
        return tours

    filtered_tours = {}
    for tour_id, tour in tours.items():
        if is_tour_in_date_range(tour, start_date, end_date):
            filtered_tours[tour_id] = tour

    date_criteria = ""
    if start_date and end_date:
        date_criteria = f"between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
    elif start_date:
        date_criteria = f"on or after {start_date.strftime('%Y-%m-%d')}"
    elif end_date:
        date_criteria = f"on or before {end_date.strftime('%Y-%m-%d')}"

    print(f"Filtered to {len(filtered_tours)} tours {date_criteria}")
    return filtered_tours

def list_tours(tours, start_date, end_date):
    tours = date_filter(tours, start_date, end_date)
    print()

    for tour_id, tour in tours.items():
        descr = tour['name'] + " (" + tour['sport'] + "; " + str(int(tour['distance']) / 1000.0) + "km; " + tour[
            'type'] + ")"
        print(bcolor.BOLD + bcolor.HEADER + str(tour_id) + bcolor.ENDC + " => " + bcolor.BOLD + descr + bcolor.ENDC)

    if len(tours) < 1:
        print_error("No tours found on your profile")

def notify_interactive():
    global interactive_info_shown
    interactive_info_shown = True
    if interactive_info_shown:
        print("Interactive mode. Use '--help' for usage details.")


def make_gpx(tour_id, api, output_dir, no_poi, skip_existing, tour_base, add_date, max_title_length, max_desc_length):
    tour = None
    if tour_base is None:
        tour_base = api.fetch_tour(str(tour_id))
        tour = tour_base

    # Example date: 2022-01-02T12:26:41.795+01:00
    # :10 extracts "2022-01-02" from this.
    date_str = tour_base['date'][:10]+'_' if add_date else ''

    filename = sanitize_filename(tour_base['name'])
    if max_title_length == 0:
        filename = f"{tour_id}"
    elif max_title_length > 0 and len(filename) > max_title_length:
        filename = f"{filename[:max_title_length]}-{tour_id}"
    else:
        filename = f"{filename}-{tour_id}"

    path = f"{output_dir}/{date_str}{filename}.gpx"

    if skip_existing and os.path.exists(path):
        print_success(f"{tour_base['name']} skipped - already exists at '{path}'")
        return

    if tour is None:
        tour = api.fetch_tour(str(tour_id))
    gpx = GpxCompiler(tour, api, no_poi, max_desc_length)

    f = open(path, "w", encoding="utf-8")
    f.write(gpx.generate())
    f.close()

    print_success(f"GPX file written to '{path}'")


def main(args):

    tour_selection = "all" if args.make_all else args.make_gpx or ""
    type_filter = args.tour_type
    max_title_length = 0 if args.id_filename else args.max_title_length

    if args.help:
        usage()
        sys.exit(2)

    mail = args.mail
    pwd = args.pwd
    anonymous = args.anonymous
    print_tours = args.list_tours
    tour_selection = args.make_gpx
    skip_existing = args.skip_existing

    if args.id_filename:
        max_title_length = 0
    elif args.max_title_length:
        max_title_length = args.max_title_length

    max_desc_length = args.max_desc_length

    add_date = args.add_date
    output_dir = args.output
    no_poi = args.no_poi

    # Parse date ranges
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print_error(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD")
            sys.exit(2)

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print_error(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD")
            sys.exit(2)

    if anonymous and tour_selection == "all":
        print_error("Cannot get all user's routes in anonymous mode, use -d")
        sys.exit(2)

    if anonymous and (mail is not None or pwd is not None):
        print_error("Cannot specify login/password in anonymous mode")
        sys.exit(2)

    api = KomootApi()

    if not anonymous:
        if mail is None:
            notify_interactive()
            mail = prompt("Enter your mail address (komoot login)")

        if pwd is None:
            notify_interactive()
            pwd = prompt_pass("Enter your password (input hidden)")

        api.login(mail, pwd)

        if print_tours:
            tours = api.fetch_tours(silent=True)
            list_tours(tours, start_date, end_date)
            sys.exit(0)

        tours = api.fetch_tours(type_filter)

        tours = date_filter(tours, start_date, end_date)

    if tour_selection is None:
        notify_interactive()
        if not anonymous:
            tours = api.fetch_tours(silent=True)
            list_tours(tours, start_date, end_date)
        tour_selection = prompt("Enter a tour id to download")

    if not anonymous and tour_selection != "all" and int(tour_selection) not in tours:
        print_warning(f"Warning: This id ({tour_selection}) is not one of your tours. Use --list-tours to view complete list.")

    if tour_selection == "all":
        for x in tours:
            make_gpx(x, api, output_dir, no_poi, skip_existing, tours[x], add_date, max_title_length, max_desc_length)
    else:
        if anonymous:
            make_gpx(tour_selection, api, output_dir, no_poi, False, None, add_date, max_title_length, max_desc_length)
        else:
            if int(tour_selection) in tours:
                make_gpx(tour_selection, api, output_dir, no_poi, skip_existing, tours[int(tour_selection)], add_date, max_title_length, max_desc_length)
            else:
                make_gpx(tour_selection, api, output_dir, no_poi, skip_existing, None, add_date, max_title_length, max_desc_length)
    print()


def entrypoint():
    args = parse_args()
    try:
        return main(args)
    except KeyboardInterrupt as e:
        print()
        print_error(f"Aborted by user: {e}")
        sys.exit(1)
    # except Exception as e:
    #     print(f"Something else went wrong: {e}")
    #     sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Komoot tours and highlights as GPX files.",
        # override the auto-created help from argparse to show usage() instead
        add_help=False
    )
    parser.add_argument("-m", "--mail", type=str, help="Email address for login")
    parser.add_argument("-p", "--pass", dest="pwd", type=str, help="Password for login")
    parser.add_argument("-n", "--anonymous", action="store_true", default=False, help="Login anonymously")
    parser.add_argument("-l", "--list-tours", action="store_true", help="Print available tours")
    parser.add_argument("-d", "--make-gpx", type=int, help="Download GPX for selected tour")
    parser.add_argument("-a", "--make-all", action="store_true", help="Download all tours")
    parser.add_argument("-s", "--skip-existing", action="store_true", help="Skip already downloaded tours")
    parser.add_argument("-I", "--id-filename", action="store_true",
                        help="Use ID as filename (max title length = 0)")
    parser.add_argument("-D", "--add-date", action="store_true", help="Add date to filename")
    parser.add_argument("--max-title-length", type=int, default=-1, help="Maximum length for titles")
    parser.add_argument("--max-desc-length", type=int, default=-1, help="Maximum length for descriptions")
    parser.add_argument("--tour-type", choices=["planned", "recorded", "all"], default="all",
                        help="Tour type to filter")
    parser.add_argument("-o", "--output", type=str, default=os.getcwd(), help="Output directory")
    parser.add_argument("-e", "--no-poi", action="store_true", help="Do not include POIs in GPX")
    parser.add_argument("--start-date", type=str, help="Filter tours on or after this date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Filter tours on or before this date (YYYY-MM-DD)")
    parser.add_argument("-h", "--help", action="store_true", help="Prints help")
    return parser.parse_args()