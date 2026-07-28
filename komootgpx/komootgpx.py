import os
import re
import sys
import argparse
import configargparse
import json
import hashlib
import shutil
from dataclasses import dataclass, fields
from datetime import datetime

from platformdirs import user_cache_dir
from colorama import init as colorama_init

from .api import KomootApi
from .gpxcompiler import GpxCompiler
from .imagedownload import ImageDownloaderWithExif
from .utils import *
from .__version__ import __version__

# in minutes
SESSION_TTL = 15

def _get_cache_dir():
    return user_cache_dir("komootgpx", ensure_exists=True)

CREDFILE = os.path.join(_get_cache_dir(), "credentials.json")
HASHFILE = os.path.join(_get_cache_dir(), "komootgpx-hashes.json")
CONFIGFILE = "config.yaml"

# Migrate credentials from old working-dir location to cache dir,
# only if the new location does not exist yet.
_old_credfile = "credentials.json"
if os.path.isfile(_old_credfile) and not os.path.isfile(CREDFILE):
    shutil.move(_old_credfile, CREDFILE)

colorama_init()
interactive_info_shown = False

output_dir_contents = set()

def usage():
    print(bcolor.HEADER + bcolor.BOLD + 'komootgpx.py [options]' + bcolor.ENDC)

    print('\n' + bcolor.OKBLUE + '[Authentication]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-m', '--mail=mail_address', 'Login using specified email address'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-p', '--pass=password', 'Use provided password and skip interactive prompt'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-n', '--anonymous', 'Skip authentication, no interactive prompt, valid only with -d'))

    print('\n' + bcolor.OKBLUE + '[Tours]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-l', '--list-tours', 'List all tours of the logged in user'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-d', '--make-gpx=tour_id', 'Download single tour as GPX'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-a', '--make-all', 'Download all tours'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-R', '--recent=N', 'Download the N most recently changed tours'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-s', '--skip-existing', 'Do not download and save GPX if the file already exists, ignored with -d'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-S', '--skip-unchanged', 'Do not download and save GPX if the tour has not changed since last download (hash verification), ignored with -d and -s'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-r', '--remove-deleted', 'Remove GPX files (from --output dir) without corresponding tour in Komoot (deleted and previous versions)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-f', '--filename-pattern=pattern', 'Specify filename pattern, default: "{title}-{id}.gpx", available fields: title, id, date, time'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-I', '--id-filename', 'Use only tour id for filename (no title), equal to -f "{id}.gpx"'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-D', '--add-date', 'Add tour date to file name, equal to -f "{date}_{title}-{id}.gpx"'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-L', '--language', 'Select description language (fr, de, en..., default: en)'))
    print('\t{:<34s} {:<10s}'.format('--max-title-length=num', 'Crop title used in filename to given length (default: -1 = no limit)'))

    print('\n' + bcolor.OKBLUE + '[Filters]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-t', '--tour-type=type', 'Filter by track type ("planned", "recorded" or "all")'))
    print('\t{:<34s} {:<10s}'.format('--start-date=YYYY-MM-DD', 'Filter tours on or after specified date (optional)'))
    print('\t{:<34s} {:<10s}'.format('--end-date=YYYY-MM-DD', 'Filter tours on or before specified date (optional)'))
    print('\t{:<34s} {:<10s}'.format('--sport=type', 'Sport type to filter (e.g. "hike")'))
    print('\t{:<34s} {:<10s}'.format('--private-only', 'Include only private tours'))
    print('\t{:<34s} {:<10s}'.format('--public-only', 'Include only public tours'))

    print('\n' + bcolor.OKBLUE + '[Generator]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-o', '--output=directory', 'Output directory (default: working directory)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-e', '--poi', 'Include highlights as POIs (default behavior)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-e', '--no-poi', 'Do not include highlights as POIs'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-K', '--karoo', 'Save all POIs with Generic type (Hammerhead Karoo import compatibility)'))
    print('\t{:<34s} {:<10s}'.format('--max-desc-length=count', 'Limit description length in characters (default: -1 = no limit)'))

    print('\n' + bcolor.OKBLUE + '[Images]' + bcolor.ENDC)
    print('\t{:<34s} {:<10s}'.format('--all-images', 'Download images from other users too - please review the copyright'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-i', '--add-images', 'Add tour images'))

    print('\n' + bcolor.OKBLUE + '[Other]' + bcolor.ENDC)
    print('\t{:<34s} {:<10s}'.format('--debug', 'Save all Komoot API responses in set of .txt files'))
    print('\t{:<34s} {:<10s}'.format('--clear-cache', 'Remove cached credentials and file hashes'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-v', '--version', 'Print version and exit'))


def is_tour_in_date_range(tour, start_date, end_date):
    if 'date' not in tour:
        if 'changed_at' in tour:
            tour['date'] = tour['changed_at']
        else:
            return True  # If tour has no date info (both date and changed_at), include it

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

def private_public_filter(tours, private_only, public_only):
    if not private_only and not public_only:
        return tours

    filtered_tours = {}
    for tour_id, tour in tours.items():
        if private_only and tour.get("status", "private") == "private":
            filtered_tours[tour_id] = tour
        elif public_only and tour.get("status", "private") != "private":
            filtered_tours[tour_id] = tour

    filter_criteria = "private only" if private_only else "public only"
    print(f"Filtered to {len(filtered_tours)} tours ({filter_criteria})")
    return filtered_tours

def sport_filter(tours, sport):
    if sport is None:
        return tours

    filtered_tours = {}
    for tour_id, tour in tours.items():
        if tour.get("sport") == sport:
            filtered_tours[tour_id] = tour

    print(f"Filtered to {len(filtered_tours)} tours (sport: {sport})")
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
    if not interactive_info_shown:
        interactive_info_shown = True
        print("Interactive mode. Use '--help' for usage details.")

@dataclass(frozen=True)
class RunConfig:
    # Run-wide configuration, built once in main() after args/config merging.
    # Only tour_id and tour_base vary between make_gpx/download_tour_images
    api: KomootApi
    output_dir: str
    filename_pattern: str
    image_dir_pattern: str
    no_poi: bool
    skip_existing: bool
    skip_unchanged: bool
    remove_deleted: bool
    max_title_length: int
    max_desc_length: int
    all_images: bool
    language: str
    karoo: bool

def make_gpx(cfg, tour_id, tour_base):
    tour = None
    if tour_base is None:
        tour_base = cfg.api.fetch_tour(str(tour_id), language=cfg.language)
        tour = tour_base

    tour_changed_at = parse_date_str(tour_base['changed_at']).timestamp()
    tour_hash = hashlib.md5(tour_base['changed_at'].encode()).hexdigest()

    hashpath = HASHFILE
    hashes = {}
    if os.path.exists(hashpath):
        with open(hashpath, "r", encoding="utf-8") as f:
            hashes = json.load(f)

    file_title = sanitize_filename(tour_base['name'])
    if cfg.max_title_length == 0:
        file_title = ""
    elif cfg.max_title_length > 0 and len(file_title) > cfg.max_title_length:
        file_title = file_title[:cfg.max_title_length]

    filename = cfg.filename_pattern.format(
        date = tour_base['date'][:10],
        time = re.sub(r'.*T(\d+):(\d+):(\d+).*', '\1:\2:\3', tour_base['date']),
        title = file_title,
        id = tour_id
        )

    fullname = sanitize_filename(filename)
    path = f"{cfg.output_dir}/{fullname}"

    if cfg.remove_deleted:
        if fullname in output_dir_contents:
            output_dir_contents.remove(fullname)

    if cfg.skip_existing and os.path.exists(path):
        print_success(f"{tour_base['name']} skipped - already exists at '{path}'")
        return

    if cfg.skip_unchanged and os.path.exists(path):
        if hashes.get(str(tour_id)) == tour_hash:
            print_success(f"{tour_base['name']} skipped - unchanged at '{path}'")
            return

    if tour is None:
        tour = cfg.api.fetch_tour(str(tour_id), language=cfg.language)

    gpx = GpxCompiler(tour, cfg.api, cfg.no_poi, cfg.max_desc_length, cfg.karoo)
    with open(path, "w", encoding="utf-8") as f:
        f.write(gpx.generate())

    # set file mtime/atime to the value of `changed_at` property of tour
    os.utime(path, (tour_changed_at, tour_changed_at))

    hashes[str(tour_id)] = tour_hash
    with open(hashpath, "w", encoding="utf-8") as f:
        json.dump(hashes, f)

    print_success(f"GPX file written to '{path}'")

def download_tour_images(cfg, tour_id, tour_base):
    if tour_base is None:
        tour_base = cfg.api.fetch_tour(str(tour_id), language=cfg.language)

    image_dir_contents = set()
    images = cfg.api.fetch_tour_images(str(tour_id), silent=False)

    if len(images) > 0:

        file_title = sanitize_filename(tour_base['name'])
        if cfg.max_title_length == 0:
            file_title = ""
        elif cfg.max_title_length > 0 and len(file_title) > cfg.max_title_length:
            file_title = file_title[:cfg.max_title_length]

        image_dir_name = cfg.image_dir_pattern.format(
            date = tour_base['date'][:10],
            time = re.sub(r'.*T(\d+):(\d+):(\d+).*', '\1:\2:\3', tour_base['date']),
            title = file_title,
            id = tour_id
            )

        image_dir_name = sanitize_filename(image_dir_name)
        image_dir = f"{cfg.output_dir}/{image_dir_name}"

        if os.path.exists(image_dir):
            imagepat = re.compile(r"\.jpg$")
            for f in os.listdir(image_dir):
                if not os.path.isfile(f) or not imagepat.match(f):
                    continue
                image_dir_contents.add(f)

    for x in images:
        creator_display_name = images[x].get('_embedded', {}).get('creator', {}).get('display_name', "")
        highlight_id = images[x].get('highlight_id', None)
        iid = images[x].get('id')
        if highlight_id and cfg.no_poi:
            print_success(f"Also skipped image download for highlight/poi: {highlight_id} (--no-poi)")
            continue

        if not cfg.all_images and creator_display_name != cfg.api.display_name:
            print_success(f"Image download skipped for image {iid} from: {creator_display_name} - it doesn't belong to user {cfg.api.display_name}")
            continue

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        third_party_copyright = ''
        if creator_display_name != cfg.api.display_name:
            third_party_copyright = '-3p'
        dt = datetime.strptime(images[x]['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        output_date = dt.strftime("%Y%m%d-%H%M%S")
        filename = sanitize_filename(output_date + "-hl" + str(x) + third_party_copyright + ".jpg")

        path = f"{image_dir}/{filename}"

        if filename in image_dir_contents:
            image_dir_contents.remove(filename)

        if cfg.skip_existing and os.path.exists(path):
            print_success(f"image download skipped - id {x} already exists at '{path}'")
            continue

        downloader = ImageDownloaderWithExif(
            images[x],
            cfg.api,
            cfg.no_poi,
            cfg.all_images,
            timezone="UTC"
        )

        saved_image = downloader.download_and_save(path)
        if saved_image:
            print_success(f"Saved {shorten_path(saved_image, 120)}")

def main(args):
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_images = args.add_images or args.all_images

    if args.make_all:
        tour_selection = "all"
    elif args.make_gpx:
        tour_selection = args.make_gpx
    elif args.recent is not None:
        tour_selection = "all"
    else:
        tour_selection = None

    tour_type_arg = f"tour_{args.tour_type}"

    filename_pattern = args.filename_pattern
    image_dir_pattern = os.path.splitext(filename_pattern)[0] + "_images"

    if args.add_date:
        filename_pattern = "{date}_" + filename_pattern
        image_dir_pattern = "{date}_" + image_dir_pattern
    elif args.id_filename:
        filename_pattern = "{id}.gpx"
        image_dir_pattern = "{id}_images"

    if args.remove_deleted:
        gpxpat = re.compile(r"\.gpx$")
        for f in os.listdir(output_dir):
            if os.path.isfile(os.path.join(output_dir, f)) and gpxpat.search(f):
                output_dir_contents.add(f)

    api = KomootApi(debug=args.debug)

    cfg = RunConfig(
        api=api,
        output_dir=output_dir,
        filename_pattern=filename_pattern,
        image_dir_pattern=image_dir_pattern,
        no_poi=args.no_poi,
        skip_existing=args.skip_existing,
        skip_unchanged=args.skip_unchanged,
        remove_deleted=args.remove_deleted,
        max_title_length=args.max_title_length,
        max_desc_length=args.max_desc_length,
        all_images=args.all_images,
        language=args.language,
        karoo=args.karoo,
    )

    if args.debug:
        resolved = {f.name: getattr(cfg, f.name) for f in fields(cfg) if f.name != "api"}
        skip = set(resolved) | {"output", "poi", "alt_no_poi"}
        resolved.update({name: value for name, value in vars(args).items() if name not in skip})

        print_info("Effective settings (defaults < config file < command line):")
        for name, value in sorted(resolved.items()):
            if name == "password":
                value = "***" if value else None  # never reveal the password
            elif isinstance(value, bool):
                value = boolToColorStr(value)
            print(f"    {name:<18} = {value}")

    mail = args.email
    pwd = args.password

    if not args.anonymous:
        token = None
        uid = None
        display_name = None
        if os.path.exists(CREDFILE):
            with open(CREDFILE, "r", encoding="utf-8") as credfile:
                creddata = json.load(credfile)
                uid = creddata.get("user_id")
                token = creddata.get("token")
                date = creddata.get("date")
                display_name = creddata.get("display_name", "(token user)")

                if datetime.now().timestamp() - date > SESSION_TTL * 60:
                    print("Stored credentials are outdated.")
                    uid = None
                    token = None
                elif uid is None or token is None:
                    print_error("Stored credentials are incomplete.")
                    os.unlink(CREDFILE)
                    sys.exit(1)

        if uid and token:
            print("Using stored credentials for user:", display_name)
            api.login_with_token(uid, token, display_name)
        else:
            if mail is None:
                notify_interactive()
                mail = prompt("Enter your mail address (komoot login)")

            if pwd is None:
                notify_interactive()
                pwd = prompt_pass("Enter your password (input hidden)")

            api.login(mail, pwd)

        with open(CREDFILE, "w", encoding="utf-8") as credfile:
            creddata = {"user_id": api.user_id, "token": api.token, "display_name": api.display_name, "date": datetime.now().timestamp()}
            json.dump(creddata, credfile)

        if args.list_tours:
            tours = api.fetch_tours(tour_type=tour_type_arg, silent=True)
            list_tours(tours, args.start_date, args.end_date)
            sys.exit(0)

        have_full_tour_list = tour_selection == "all" or tour_selection is None
        if have_full_tour_list:
            tours = api.fetch_tours(tour_type_arg)
            tours = date_filter(tours, args.start_date, args.end_date)
            tours = private_public_filter(tours, args.private_only, args.public_only)
            tours = sport_filter(tours, args.sport)

            if args.recent is not None:
                sorted_tours = sorted(tours.items(), key=lambda x: x[1].get('changed_at', ''), reverse=True)
                tours = dict(sorted_tours[:args.recent])
                print(f"Limited to {len(tours)} most recently changed tours")
        else:
            tours = {}

    if tour_selection is None:
        notify_interactive()
        if not args.anonymous:
            tours = api.fetch_tours(tour_type=tour_type_arg, silent=True)
            list_tours(tours, args.start_date, args.end_date)
        tour_selection = prompt("Enter a tour id to download")

    if not args.anonymous and tour_selection != "all" and have_full_tour_list and int(tour_selection) not in tours:
        print_warning(f"Warning: This id ({tour_selection}) is not one of your tours. Use --list-tours to view complete list.")

    if tour_selection == "all":
        for x in tours:
            make_gpx(cfg, x, tours[x])
            if process_images and not args.anonymous:
                download_tour_images(cfg, x, tours[x])
    else:
        if args.anonymous:
            make_gpx(cfg, tour_selection, None)
            if process_images:
                print_warning(f"Warning: No image download in anonymous mode.")
        else:
            if int(tour_selection) in tours:
                make_gpx(cfg, tour_selection, tours[int(tour_selection)])
                if process_images:
                    download_tour_images(cfg, tour_selection, tours[int(tour_selection)])
            else:
                make_gpx(cfg, tour_selection, None)
                if process_images:
                    download_tour_images(cfg, tour_selection, None)

    if args.remove_deleted:
        for f in output_dir_contents:
            os.unlink(os.path.join(output_dir, f))
            print_success(f"{f} removed from {output_dir}")

def entrypoint():
    args = parse_args()
    try:
        return main(args)
    except KeyboardInterrupt as e:
        print()
        print_error(f"Aborted by user: {e}")
        sys.exit(1)

def parse_args():
    parser = configargparse.ArgParser(
        description="Download Komoot tours and highlights as GPX files.",
        default_config_files=[CONFIGFILE],
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        # override the auto-created help to show usage() instead
        add_help=False
    )

    parser.add_argument("-m", "--mail", "--email", type=str, dest="email", help="Email address for login")
    parser.add_argument("-p", "--pass", "--password", type=str, dest="password", help="Password for login")
    parser.add_argument("-n", "--anonymous", action="store_true", help="Login anonymously")

    parser.add_argument("-l", "--list-tours", action="store_true", help="Print available tours")
    parser.add_argument("-d", "--make-gpx", type=int, help="Download GPX for selected tour")
    parser.add_argument("-a", "--make-all", action="store_true", help="Download all tours")
    parser.add_argument("-R", "--recent", type=int, default=None, help="Download the N most recently changed tours")
    # NOTE: for BooleanOptionalAction the long option MUST be listed before the
    # short one. ConfigArgParse serialises a config value using the *first*
    # option string; if a short positive flag like "-s" comes first, a config
    # entry "skip-existing: false" is silently turned into True. Long-first lets
    # it emit "--no-skip-existing" and honour the false value.
    parser.add_argument("--skip-existing", "-s", action=argparse.BooleanOptionalAction, default=False, help="Skip already downloaded tours")
    parser.add_argument("--skip-unchanged", "-S", action=argparse.BooleanOptionalAction, default=False, help="Skip tours that have not changed since last download (uses hash verification)")
    parser.add_argument("--remove-deleted", "-r", action=argparse.BooleanOptionalAction, default=False, help="Remove gpx files for nonexistent tours")
    parser.add_argument("-f", "--filename-pattern", type=str, default="{title}-{id}.gpx", help="Filename pattern")
    parser.add_argument("-I", "--id-filename", action="store_true", help="Use tour ID as filename")
    parser.add_argument("-D", "--add-date", action="store_true", help="Prepend filename with tour modification date")
    parser.add_argument("--max-title-length", type=int, default=-1, help="Maximum length for titles")
    parser.add_argument("-L", "--language", type=str, default="en", help="Select description language (default=en)")

    parser.add_argument("-t", "--tour-type", choices=["planned", "recorded", "all"], default="all", help="Tour type to filter")
    parser.add_argument("--start-date", type=str, help="Filter tours on or after this date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Filter tours on or before this date (YYYY-MM-DD)")
    parser.add_argument("--sport", type=str, help="Sport type to filter (e.g., 'hike')")
    parser.add_argument("--private-only", action="store_true", help="Include only private tours")
    parser.add_argument("--public-only", action="store_true", help="Include only public tours")

    parser.add_argument("-o", "--output", type=str, default=os.getcwd(), help="Output directory")
    # --poi / -e keep default=None to resolve no_poi later
    parser.add_argument("--poi", action=argparse.BooleanOptionalAction, default=None, help="Include POIs in GPX")
    parser.add_argument("-e", "--alt-no-poi", action="store_true", default=None, help="Do not include POIs in GPX")
    parser.add_argument("--karoo", "-K", action=argparse.BooleanOptionalAction, default=False, help="Save all POIs with Generic type (Hammerhead Karoo import compatibility)")
    parser.add_argument("--max-desc-length", type=int, default=-1, help="Maximum length for descriptions")

    parser.add_argument("--add-images", "-i", action=argparse.BooleanOptionalAction, default=False, help="Add tour images")
    parser.add_argument("--all-images", action=argparse.BooleanOptionalAction, default=False, help="Download images from other users too - please review the copyright")

    parser.add_argument("--debug", action="store_true", default=False, help="Debug")

    parser.add_argument("--clear-cache", action="store_true", help="Clear cached credentials and file hashes")
    parser.add_argument("-h", "--help", action="store_true", help="Prints help")
    parser.add_argument("-v", "--version", action="store_true", help="Prints version")

    args = parser.parse_args()

    if args.help:
        usage()
        sys.exit(0)

    if args.clear_cache:
        for f in (CREDFILE, HASHFILE):
            if os.path.isfile(f):
                os.unlink(f)
                print_success(f"Removed {f}")
        sys.exit(0)

    # Resolve POI handling into a single derived flag `no_poi`.
    # `-e`/`--alt-no-poi` is a backward-compatible alias for `--no-poi`
    # Precedence (default < config `poi:` < `--poi` / `--no-poi`) is handled for `poi` by ConfigArgParse
    # `-e` then forces exclusion on top of that
    if args.alt_no_poi or args.poi is False:  # -e OR --no-poi (or config poi: false)
        args.no_poi = True
    else:  # --poi, or nothing specified -> default is to include POIs
        args.no_poi = False

    # validation rules
    if args.anonymous and (args.email is not None or args.password is not None):
        print_error("Cannot specify login/password in anonymous mode")
        sys.exit(2)

    if args.make_all and args.make_gpx:
        print_error("Cannot specify both -d and -a (--make-gpx and --make-all)")
        sys.exit(2)

    if args.recent is not None and args.make_gpx:
        print_error("Cannot specify both -d and -R (--make-gpx and --recent)")
        sys.exit(2)

    if args.recent is not None and args.make_all:
        print_error("Cannot specify both -a and -R (--make-all and --recent)")
        sys.exit(2)

    if args.anonymous and (args.make_all or args.recent is not None):
        print_error("Cannot get all user's routes in anonymous mode, use -d")
        sys.exit(2)

    if args.remove_deleted and not args.make_all:
        print_error("--remove-deleted works only with --make-all")
        sys.exit(2)

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

    args.start_date = start_date
    args.end_date = end_date

    if args.debug:
        print(parser.format_values())
        print()

    return args
