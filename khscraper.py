# -*- coding: utf-8 -*-
#
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
import datetime
import urllib.parse
import urllib.request
import progressbar # progressbar2 package (Progress bar display)
from bs4 import BeautifulSoup # beautifulsoup4 package (Web scraping class)
from tabulate import tabulate # tabulate package (Tabulate table class)

class KHSong(object):
    """Describe a khinsider song

    Attributes
        name (str) : Name of the song
        duration (str) : Duration of the song
        size (str) : Size of the song
        href (str) : The hypertext reference to download song
    """
    def __init__(self, name, duration, size, href):
        """KHSong __init__ method"""

        self.name = name
        self.duration = duration
        self.size = size
        self.url = "https://downloads.khinsider.com" + href
        self.pbar = None

    def __scrape_download_link_from_url(self, url):
        """Scrape khinsider song download link from URL

        Parameters
            url (str) : The khinsider song URL to look for

        Return
            The khinsider song download link as a string
        """

        html = self.__get_html_from_url(url)
        return self.__scrape_download_link_from_html(html)

    def __get_html_from_url(self, url):
        """Get HTML document from URL

        Parameters
            url (str) : The URL to look for

        Return
            The HTML document as a string
        """

        fp = urllib.request.urlopen(url)
        html = fp.read().decode("utf8")
        fp.close()

        return html

    def __scrape_download_link_from_html(self, html):
        """Scrape khinsider song download link from HTML document

        Parameters
            html (str) : The khinsider game HTML document to look for

        Return
            The khinsider song download link as a string
        """

        soup = BeautifulSoup(html, 'html.parser')

        # Khinsider always had a "songDownloadLink" class in a nestsed span
        tag = soup.find(lambda tag: tag.name == 'span' and tag.has_attr('class') and 'songDownloadLink' in tag['class'])

        return tag.parent.get('href')

    def __update_progress(self, count, block_size, total_size):
        """Update progress bar (Callback function)

        Parameters
            count (int) : A block number
            block_size (int) : The maximum size blocks are read in
            total_size (int) : Total size of the download

        Return
            None
        """

        if self.pbar is None:
            self.pbar = progressbar.DataTransferBar(max_value=total_size)

        downloaded = count * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()

    def get_info(self, num):
        """Get khinsider song informations

        Parameters
            num (int) : Song number in the khinsider song list

        Return
            The khinsider song informations as a list
        """

        return [num, self.name, self.duration, self.size]

    def download(self, path, verbosity=False):
        """Download khinsider song

        Parameters
            path (str) : Path where to download song
            verbosity (boolean) : Verbosity flag (True/False) to display more informations

        Return
            The time elapsed to download song as a timedelta object
        """

        link = self.__scrape_download_link_from_url(self.url)
        if verbosity:
            print("Link found: " + link)
        file = os.path.basename(urllib.parse.unquote(link))
        urllib.request.urlretrieve(link, os.path.join(path, file), reporthook=self.__update_progress)
        time_elapsed = self.pbar.data()['time_elapsed']

        # Reset progress bar
        self.pbar = None

        return time_elapsed

class KHScraper(object):
    """Describe a khinsider game scraping attempt (aka. its songlist)

    Attributes
        url (str) : The khinsider game URL
        output (str) : The output directory for download (Default is execution directory) [optional]
        verbosity (boolean) : A verbosity flag (True/False) to display more informations [optional]
    """

    def __init__(self, url, output='.', verbosity=False):
        """KHScraper __init__ method"""

        if not url.startswith("https://downloads.khinsider.com/game-soundtracks/album/"):
            raise ValueError(f"'{url}' is not a valid khinsider URL")

        if not os.path.isdir(output):
            raise ValueError(f"'{output}' is not a directory")

        self.url = url
        self.output = output + '/' if not output.endswith('/') else output
        self.verbosity = verbosity
        self.songlist = self.__scrape_songlist_from_url(self.url)

    def __scrape_songlist_from_url(self, url):
        """Scrape khinsider game song list from URL

        Parameters
            url (str) : The khinsider game URL to look for

        Return
            The khinsider game song list as a list
        """

        html = self.__get_html_from_url(url)
        return self.__scrape_songlist_from_html(html)

    def __get_html_from_url(self, url):
        """Get HTML document from URL

        Parameters
            url (str) : The URL to look for

        Return
            The HTML document as a string
        """

        fp = urllib.request.urlopen(url)
        html = fp.read().decode("utf8")
        fp.close()

        return html

    def __scrape_songlist_from_html(self, html):
        """Scrape khinsider game song list from HTML document

        Parameters
            html (str) : The khinsider game HTML document to look for

        Return
            The khinsider game song list as a list
        """

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
                    songlist.append(KHSong(texts[index], texts[index+1], texts[index+2], href))
                    break

        return songlist


    def __strfdelta(self, tdelta, fmt):
        """Format a timedelta object with 'days', 'hours', 'min' and 'sec' placeholders

        Parameters
            tdelta (timedelta object) : The timedelta object to format
            fmt (str) : String to format

        Return
            The formatted timedelta object as a string
        """

        d = {"days": tdelta.days}
        d["hours"], rem = divmod(tdelta.seconds, 3600)
        d["min"], d["sec"] = divmod(rem, 60)
        return fmt.format(**d)


    def print(self):
        """Pretty-print khinsider game song list in a table

        Parameters
            None

        Return
            None
        """

        table = []
        headers = ['N.', 'Track', 'Duration', 'Size']

        for index, song in enumerate(self.songlist):
            table.append(song.get_info(index+1))

        print(tabulate(table, headers))

    def query_yes_no(self, question, default='yes'):
        """Prompt user for a boolean choice

        Parameters
            question (str) : Question to ask to user
            default (str) : Default answer (Default is 'yes') [optional]

        Return
            A boolean representing user choice
        """

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

    def download(self):
        """Download khinsider game song list

        Parameters
            None

        Return
            None
        """

        total_time_elapsed = datetime.timedelta()

        print(f"Output directory: '{self.output}'")
        for index, song in enumerate(self.songlist):
            print(f"Downloading '{song.name}' [{index+1}/{len(self.songlist)}]...")
            total_time_elapsed += song.download(self.output, self.verbosity)

        print(f"Total time elapsed:" + self.__strfdelta(total_time_elapsed, ' {days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)'))

if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(description="Extract song list from a khinsider game URL")
    parser.add_argument('-o', '--output', default='.', help="Directory output (Default is execution directory)")
    parser.add_argument('-v', '--verbose', default=False, action="store_true", help="More informations displayed")
    parser.add_argument('url', help="Khinsider URL")

    args = parser.parse_args()

    # Scrap game song list
    scraper = KHScraper(args.url, args.output, args.verbose)

    # Display songlist
    scraper.print()

    # Prompt user
    if scraper.query_yes_no("\nIs this ok ?", 'yes') == False:
        sys.exit(0)

    # Download songlist
    scraper.download()
