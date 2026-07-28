# KomootGPX
Download Komoot tracks and highlights as GPX files with metadata

[Python 3 or later](https://www.python.org/downloads/) is required.

## Features
* Download recorded & planned trips as GPX files
* Bulk-download all trips stored in your profile (requires authentication)
* Includes metadata such as estimated duration, total elevation, difficulty and the original Komoot trip URL
* Can add trip highlights as POIs into the GPX file
  * Includes user comments & image URLs for each highlight POI, as those often contain helpful information about the location
  * Additionally custom Komoot waypoints can be added as POIs


## Installation
Download from [PyPI](https://pypi.org/project/komootgpx/):
```
pip install komootgpx
```

## Testing
To run from local clone of repo (without installation):
```
uv run python -m komootgpx --help
```

## Usage

### Run script in interactive mode
```
uv run komootgpx
```
```
Enter your mail address (komoot.de)
>example@mail.com

Enter your password (input hidden)
Password:

Logging in...
Logged in as 'Example User'

3331210XX => Example trip A (hike; 20.766km; tour_recorded)
3331214XX => Example trip B (hike; 13.863km; tour_planned)

Enter a tour id to download
>3331210XX

Fetching tours of user '153434028XXX'...
Fetching tour '3331210XX'...
Fetching highlight '2635XX'...
Fetching highlight '15840XX'...
GPX file written to 'Example trip A-3331210XX.gpx'
```

### Display advanced usage information
```
komootgpx --help
```
```
komootgpx.py [options]

[Authentication]
        -m, --mail=mail_address            Login using specified email address
        -p, --pass=password                Use provided password and skip interactive prompt
        -n, --anonymous                    Skip authentication, no interactive prompt, valid only with -d

[Tours]
        -l, --list-tours                   List all tours of the logged in user
        -d, --make-gpx=tour_id             Download single tour as GPX
        -a, --make-all                     Download all tours
        -R, --recent=N                     Download the N most recently changed tours
        -s, --skip-existing                Do not download and save GPX if the file already exists, ignored with -d
        -S, --skip-unchanged               Do not download and save GPX if the tour has not changed since last download (hash verification), ignored with -d and -s
        -r, --remove-deleted               Remove GPX files (from --output dir) without corresponding tour in Komoot (deleted and previous versions)
        -f, --filename-pattern=pattern     Specify filename pattern, default: "{title}-{id}.gpx", available fields: title, id, date, time
        -I, --id-filename                  Use only tour id for filename (no title), equal to -f "{id}.gpx"
        -D, --add-date                     Add tour date to file name, equal to -f "{date}_{title}-{id}.gpx"
        -L, --language                     Select description language (fr, de, en..., default: en)
        --max-title-length=num             Crop title used in filename to given length (default: -1 = no limit)

[Filters]
        -t, --tour-type=type               Filter by track type ("planned", "recorded" or "all")
        --start-date=YYYY-MM-DD            Filter tours on or after specified date (optional)
        --end-date=YYYY-MM-DD              Filter tours on or before specified date (optional)
        --sport=type                       Sport type to filter (e.g. "hike")
        --private-only                     Include only private tours
        --public-only                      Include only public tours

[Generator]
        -o, --output=directory             Output directory (default: working directory)
        --poi                              Include highlights as POIs (default behavior)
        -e, --no-poi                       Do not include highlights as POIs
        -K, --karoo                        Save all POIs with Generic type (Hammerhead Karoo import compatibility)
        --max-desc-length=count            Limit description length in characters (default: -1 = no limit)

[Images]
        --all-images                       Download images from other users too - please review the copyright
        -i, --add-images                   Add tour images

[Other]
        --debug                            Save all Komoot API responses in set of .txt files
        --clear-cache                      Remove cached credentials and file hashes
        -v, --version                      Print version and exit
```

### Authentication
It's required to be properly authenticated with username (email) and password to perform most of available operations:
 * list user's tours (both planned and completed)
 * download all tours
 * download tour that has Visibility set to "Only me" or "Close friends"

Without authentication you can download any tour that is public (i.e. Visibility set to "Anyone"). To disable authentication use `--anonymous` option.

In case given tour id is not available without authentication you'll receive following message: `Error 403: {'status': 403, 'error': 'AccessDenied', 'message': 'Access denied without authentication.'}`.

Once you've logged in, the API token will be cached and reused for future requests, so you don't need to re-authenticate until the token expires.

> [!NOTE]
> The API token (and tour hashes) are cached in the system's cache directory (`~/.cache/komootgpx` on Linux,
> `~/Library/Caches/komootgpx` on macOS, `%LOCALAPPDATA%/komootgpx/Cache` on Windows).
> Use `--clear-cache` to remove these cached files.

### Configuration file

You can create an optional `config.yaml` file in the directory you run `komootgpx` from (the output directory).

The config file lets you set default values for options like the filename pattern, output directory, or other CLI flags, 
so you don't need to pass them every time. 

Command-line flags always override values set in the config file. Boolean flags that were set to true in the config file can be unset with long negated flag, e.g. `--no-remove-deleted`.

A [`config.yaml.example`](config.yaml.example) template file is provided in the repository. Copy it to `config.yaml` and adjust the values as a starting point.

```yaml
# KomootGPX configuration file (config.yaml)
#
# Every key is a long command-line option name without the leading "--".
# Values set here override the built-in defaults, and are in turn overridden by options given on the command line.

# --- Authentication ---
# email:                                 # -m  Login email (default: prompt)
# password:                              # -p  Login password (default: prompt)
anonymous: false                         # -n  Skip authentication (valid only with -d)

# --- Tours ---
list-tours: false                        # -l  List all tours and exit
# make-gpx:                              # -d  Download single tour by id (default: unset)
make-all: false                          # -a  Download all tours
# recent:                                # -R  Download the N most recently changed tours (default: unset)
skip-existing: false                     # -s  Skip tours whose file already exists
skip-unchanged: false                    # -S  Skip tours unchanged since last download (hash check)
remove-deleted: false                    # -r  Remove GPX files without a corresponding tour
filename-pattern: "{title}-{id}.gpx"     # -f  Filename pattern (fields: title, id, date, time)
id-filename: false                       # -I  Use only tour id as filename (= -f "{id}.gpx")
add-date: false                          # -D  Prepend tour date (= -f "{date}_{title}-{id}.gpx")
language: en                             # -L  Description language (fr, de, en, ...)
max-title-length: -1                     #     Crop title in filename to N chars (-1 = no limit)

# --- Filters ---
tour-type: all                           # -t  Track type: planned, recorded or all
# start-date:                            #     Include tours on or after YYYY-MM-DD (default: unset)
# end-date:                              #     Include tours on or before YYYY-MM-DD (default: unset)
# sport:                                 #     Sport type filter, e.g. hike (default: unset)
private-only: false                      #     Include only private tours
public-only: false                       #     Include only public tours

# --- Generator ---
output: .                                # -o  Output directory (default: working directory)
poi: true                                # -e  Include highlights as POIs; false == -e / --no-poi
karoo: false                             # -K  Save all POIs with Generic type (Karoo compatibility)
max-desc-length: -1                      #     Crop description to N chars (-1 = no limit)

# --- Images ---
all-images: false                        #     Download images from other users too (check copyright)
add-images: false                        # -i  Download tour images

# --- Other ---
debug: false                             #     Save all Komoot API responses to .txt files
clear-cache: false                       #     Remove cached credentials and file hashes, then exit
```

