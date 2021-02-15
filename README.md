# khscraper

`khscraper` is a [khinsider](http://downloads.khinsider.com/) scraping tool coded in [Python](https://www.python.org/).
It allows you to download all songs hosted on khinsider for a given album URL.
By default, khinsider has disabled the all-in-one feature. This program attempts to re-automate the process.

# Dependencies

Python dependencies:

- [python3](https://www.python.org/) >= 3.6 : Use python3 instead of python2
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
- Choose the output directory
- Choose the quality format (MP3, FLAC, OGG, ...)
- Choose the start index in the album song list
- Choose the end index in the album song list
- Enable verbose mode

You can also import the module in another project:

```python
import khscraper
album = KHAlbum(url)

# Get album informations
album.get_name()
album.get_available_formats()
album.get_songlist()

# Print album informations
album.print()

# Download album song list
album.download([output=], [fmt=] [start=] [end=] [verbose=])
```

# Author(s)

Droidec (Marc G.) <https://github.com/Droidec>

# Licence

`khscraper` is released under BSD-3 clause licence. See the LICENCE file in this source distribution for more information.
