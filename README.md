# khscraper

`khscraper` is a [khinsider](http://downloads.khinsider.com/) scraping tool coded in [Python](https://www.python.org/).
It allows you to download all songs hosted on khinsider for a given album URL.
By default, khinsider has disabled the all-in-one download feature. This program attempts to re-automate the process.

# Dependencies

Python dependencies:

- [python3](https://www.python.org/) >= 3.6 : Use python3 instead of python2
- [requests](https://pypi.org/project/requests/) >= 2.25.1 : To download [khinsider](http://downloads.khinsider.com/) content
- [progressbar2](https://pypi.org/project/progressbar2/) >= 3.53.1 : To display a progress bar for each download
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) >= 4.9.3 : To scrape [khinsider](http://downloads.khinsider.com/) informations
- [tabulate](https://pypi.org/project/tabulate/) >= 0.8.7 : To pretty-print song list

# Usage

From the command line, simply call the python script as follows:

```cmd
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/amnesia
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/hitman-2-soundtrack
python3 khscraper.py https://downloads.khinsider.com/game-soundtracks/album/kingdom-hearts-ii-ost
```

Available options:
- Display help (-h, --help)
- Choose download format (MP3, FLAC, OGG, ...) (-f, --format)
- Choose output directory (-o, --output)
- Choose start index in the album song list (--start)
- Choose end index in the album song list (--end)
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
album.get_songlist() # List of KHSong objects

# Print album informations
album.print()

# Download album song list
album.download([output=], [fmt=], [start=], [end=], [covers=], [verbose=])
```

# Author(s)

Droidec (Marc G.) <https://github.com/Droidec>

# Licence

`khscraper` is released under BSD-3 clause licence. See the LICENCE file in this source distribution for more information.
