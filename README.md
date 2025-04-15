# KomootGPX
Download Komoot tracks and highlights as GPX files with metadata

[Python 3 or later](https://www.python.org/downloads/) is required.

## Features
* Download recorded & planned trips as GPX files
* Bulk-download all trips stored in your profile (requires authentication)
* Includes metadata such as estimated duration, total elevation, difficulty and the original Komoot trip URL
* Can add trip highlights as POIs into the GPX file
  * Includes user comments & image URLs for each highlight POI, as those often contain helpful information about the location


## Installation
Download from [PyPI](https://pypi.org/project/komootgpx/):
```
pip install komootgpx
```

## Testing
To run from local clone of repo (without installation):
```
python -m komootgpx --help
```

## Usage

### Run script in interactive mode
```
komootgpx
```
```
Enter your mail address (komoot.de)
>example@mail.com

Enter your password (input hidden)
Password:

Logging in...
Logged in as 'thepbone'

3331210XX => Example trip A (hike; 20.766km; tour_recorded)
3331214XX => Example trip B (hike; 13.863km; tour_planned)

Enter a tour id to download
>3331210XX

Fetching tours of user '153434028XXX'...
Fetching tour '3331210XX'...
Fetching highlight '2635XX'...
Fetching highlight '15840XX'...
GPX file written to '~/Development/KomootGPX/Example trip A-3331210XX.gpx'
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
        -d, --make-gpx=tour_id             Download tour as GPX
        -a, --make-all                     Download all tours
        -s, --skip-existing                Do not download and save GPX if the file already exists, ignored with -d
        -I, --id-filename                  Use only tour id for filename (no title)
        -D, --add-date                     Add date to file name
        --max-title-length=num             Crop title used in filename to given length (default: -1 = no limit)

[Filters]
        -f, --filter=type                  Filter by track type (either "planned" or "recorded")

[Generator]
        -o, --output                       Output directory (default: working directory)
        -e, --no-poi                       Do not include highlights as POIs
        --max-desc-length=count            Limit description length of POIs in characters (default: -1 = no limit)
```

### Authentication
It's required to be properly authenticated with username (email) and password to perform most of available operations:
 * list user's tours (both planned and completed)
 * download all tours
 * download tour that has Visibility set to "Only me" or "Close friends"

Without authentication you can download any tour that is public (i.e. Visibility set to "Anyone"). To disable authentication use `--anonymous` option.

In case given tour id is not available without authentication you'll receive following message: `Error 403: {'status': 403, 'error': 'AccessDenied', 'message': 'Access denied without authentication.'}`.

