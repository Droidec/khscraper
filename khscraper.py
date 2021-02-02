# Copyright (c) 2019-2021, Droidec (Marc G.)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of Thomas J Bradley nor the names of its contributors may
#    be used to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import os
import sys
import argparse
import urllib.parse
import urllib.request
import progressbar # progressbar2 package (Progress bar display)
from bs4 import BeautifulSoup # beautifulsoup4 package (Web scraping class)
from tabulate import tabulate # tabulate package (Tabulate table class)

def get_html_from_url(url):
        """Extract HTML from URL"""
        fp = urllib.request.urlopen(url)

        html = fp.read().decode("utf8")
        fp.close()

        return html

def query_yes_no(question, default='yes'):
    """Ask user if he wants to download song list"""
    valid = {
        'yes': True,
        'ye': True,
        'y': True,
        'no': False,
        'n': False
    }
    if default is None:
        prompt = " [y/n] "
    elif default == 'yes':
        prompt = " [Y/n] "
    elif default == 'no':
        prompt = " [y/N] "
    else:
        raise ValueError(f"Invalid default value: '{default}'")

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]

class Song(object):
    """Song class

    Describe a song (name, duration, size, ...)
    """
    def __init__(self, name, duration, size, href):
        self.name = name
        self.duration = duration
        self.size = size
        self.url = "https://downloads.khinsider.com" + href
        self.pbar = None

    def __get_download_link_from_url(self, url):
        """Extract download link from URL"""

        html = get_html_from_url(url)
        return self.__get_download_link_from_html(html)

    def __get_download_link_from_html(self, html):
        """Extract download link from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Khinsider always had a "songDownloadLink" class in a nestsed span
        tag = soup.find(lambda tag: tag.name == 'span' and tag.has_attr('class') and 'songDownloadLink' in tag['class'])

        return tag.parent.get('href')

    def __show_progress(self, count, block_size, total_size):
        if self.pbar is None:
            self.pbar = progressbar.ProgressBar(maxval=total_size)

        downloaded = count * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()
            self.pbar = None

    def get_info(self):
        """Return song informations as a list"""
        return [self.name, self.duration, self.size]

    def download(self, path, verbosity=False):
        """Download song"""
        link = self.__get_download_link_from_url(self.url)
        if verbosity:
            print("Link found: " + link)
        file = os.path.basename(urllib.parse.unquote(link))
        urllib.request.urlretrieve(link, os.path.join(path, file), reporthook=self.__show_progress)

class Scraper(object):
    """Scraper class

    Read khinsider game URL page, extract songlist and download them
    """
    def __init__(self, url, output='.', verbosity=False):

        if not url.startswith("https://downloads.khinsider.com/game-soundtracks/album/"):
            raise ValueError(f"'{url}' is not a valid khinsider URL")

        if not os.path.isdir(output):
            raise ValueError(f"'{output}' is not a directory")

        self.url = url
        self.output = output + '/' if not output.endswith('/') else output
        self.verbosity = verbosity
        self.songlist = self.__get_songlist_from_url(self.url)

    def __get_songlist_from_url(self, url):
        """Extract songlist from URL"""

        html = get_html_from_url(url)
        return self.__get_songlist_from_html(html)

    def __get_songlist_from_html(self, html):
        """Extract songlist from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        songlist = []

        # Khinsider always has a table id called "songlist"
        table = soup.find(lambda tag: tag.name == 'table' and tag.has_attr('id') and tag['id'] == "songlist")

        # Eliminate header/footer of the table
        rows = table.find_all(lambda tag: tag.name == 'tr')[1:-1]

        # Get every song
        for row in rows:
            cols = row.find_all('td')
            texts = [x.text.strip() for x in cols]

            for index, col in enumerate(cols):
                # Khinsider always had a "clickable-row" class for href
                if col.has_attr('class') and 'clickable-row' in col['class']:
                    href = col.find('a').get('href')
                    # We assume that duration and size are in the next columns
                    songlist.append(Song(texts[index], texts[index+1], texts[index+2], href))
                    break

        return songlist

    def print_songlist(self):
        """Print extracted songlist"""
        table = []
        headers = ['Track', 'Duration', 'Size']

        for song in self.songlist:
            table.append(song.get_info())

        print(tabulate(table, headers))

    def download_songlist(self):
        """Download extracted songlist"""
        print(f"Output directory: '{self.output}'")
        for index, song in enumerate(self.songlist):
            print(f"Downloading '{song.name}' [{index+1}/{len(self.songlist)}]...")
            song.download(self.output, self.verbosity)

if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(description="Extract song list from a khinsider game URL")
    parser.add_argument('-o', '--output', default='.', help="Directory output (Default is execution directory)")
    parser.add_argument('-v', '--verbose', default=False, action="store_true", help="More informations displayed")
    parser.add_argument('url', help="Khinsider URL")

    args = parser.parse_args()

    # Analyze URL
    scraper = Scraper(args.url, args.output, args.verbose)

    # Display songlist
    scraper.print_songlist()

    # Prompt user
    if query_yes_no("\nIs this ok ?", 'yes') == False:
        sys.exit(0)

    # Download songlist
    scraper.download_songlist()
