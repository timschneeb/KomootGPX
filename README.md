# KomootGPX
Download Komoot tracks and highlights as GPX files with metadata

[Python 3 or later](https://www.python.org/downloads/) is required.

## Installation
Download from [PyPI](https://pypi.org/project/komootgpx/):
```
pip install komootgpx
```
## Usage

Run script in interactive mode
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

Display advanced usage information
```
komootgpx --help
```
```
komootgpx.py [options]
[Authentication]
        -m, --mail=mail_address            Login using specified email address
        -p, --pass=password                Use provided password and skip interactive prompt
[Tours]
        -l, --list-tours                   List all tours of the logged in user
        -d, --make-gpx=tour_id             Download tour as GPX
        -a, --make-all                     Download all tours
        -D, --add-date                     Add date to file name
[Filters]
        -f, --filter=type                  Filter by track type (either "planned" or "recorded")
[Generator]
        -o, --output                       Output directory (default: working directory)
        -e, --no-poi                       Do not include highlights as POIs
```
