# khscraper

`khscraper` is a [khinsider](http://downloads.khinsider.com/) scraping tool coded in [Python](https://www.python.org/).
It allows you to download all songs hosted on khinsider for a given album URL.
By default, khinsider has disabled the all-in-one download feature. This program attempts to re-automate the process.

## Dependencies

Python dependencies:

- [python3](https://www.python.org/) >= 3.12 : Use python3 interpreter
- [requests](https://pypi.org/project/requests/) >= 2.32.3 : To download [khinsider](http://downloads.khinsider.com/) hosted files
- [progressbar2](https://pypi.org/project/progressbar2/) >= 4.4.2 : To display a progress bar for each download
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) >= 4.12.3 : To scrape [khinsider](http://downloads.khinsider.com/) content
- [tabulate](https://pypi.org/project/tabulate/) >= 0.9.0 : To pretty-print tracklist

## Usage

From the command line, simply call the python script as follows:

```cmd
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/amnesia
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/hitman-2-soundtrack
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/kingdom-hearts-ii-ost
```

Available options:
- Display help (-h, --help)
- Choose output directory (-o, --output)
- Choose download format (MP3, FLAC, OGG, ...) (-f, --format)
- Set inactivity timeout in seconds (-t, --timeout)
- Set chunk size in bytes for covers/songs download (--chunk)
- Choose start index in the album tracklist (--start)
- Choose end index in the album tracklist (--end)
- Download covers (-c, --covers)
- Enable verbose mode (-v, --verbose)

You can also import the module in another project:

```python
import khscraper
album = KHAlbum(url)

# Get album informations (if needed)
album.get_name()
album.get_available_formats()
album.get_covers() # List of KHCover objects
album.get_tracklist() # List of KHSong objects

# Print album informations
album.print()

# Download album song list
album.download([output=], [fmt=], [timeout=], [chunk_size=], [start=], [end=], [dlcovers=], [verbose=])
```

## Author

Marc GIANNETTI \<mgtti.pro@gmail.com\>

## Licence

`khscraper` is released under BSD-3 clause licence.  
See the LICENCE file in this source distribution for more information.
