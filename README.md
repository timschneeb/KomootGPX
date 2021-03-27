# KomootGPX
Download Komoot tracks and highlights as GPX files with metadata

[Python 3 or later](https://www.python.org/downloads/) is required.

Install dependencies
```
pip install -r requirements.txt
```

# Usage

Run script in interactive mode
```
python komoot-gpx.py
```
```
Enter your mail address (komoot.de)
>example@mail.com

Enter your password (input hidden)
Password:

Logging in...
Logged in as 'thepbone'

3331210XX => Example trip A (hike, 20.766km)
3331210XX => Example trip B (hike, 13.863km)

Enter a tour id to download
>333314804

Fetching tours of user '153434028XXX'...
Fetching tour '33331210XX'...
Fetching highlight '2635XX'...
Fetching highlight '15840XX'...
Fetching highlight '20981XX'...
Fetching highlight '875XX'...
GPX file written to 'D:\Development\KomootGPX\Example trip A.gpx'
```

Display advanced usage information
```
python komoot-gpx.py --help
```
```
komoot-gpx.py [options]
[Authentication]
        -m, --mail=mail_address            Login using specified email address
        -p, --pass=password                Use provided password and skip interactive prompt
[Tours]
        -l, --list-tours                   List all tours of the logged in user
        -d, --make-gpx=tour_id             Download tour as GPX
        -a, --make-all                     Download all tours
[Generator]
        -o, --output                       Output directory (default: working directory)
        -e, --no-poi                       Do not include highlights as POIs
```
