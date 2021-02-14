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
import collections
import urllib.parse
import urllib.request

import progressbar # progressbar2 package
from bs4 import BeautifulSoup # beautifulsoup4 package
from tabulate import tabulate # tabulate package

def get_html_from_url(url):
    """Get HTML document from URL

    Parameters
        url (str) : URL to look for

    Return
        The HTML document as a string
    """

    fp = urllib.request.urlopen(url)
    html = fp.read().decode("utf8")
    fp.close()

    return html

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

class KHSong(object):
    """KHSong describe a KHinsider song

    Attributes
        url (str) : KHinsider song URL
        attr (OrderDict) : Song attributes (name, duration, formats ...)
    """

    def __init__(self, url, attr):
        """KHSong init"""
        self.url = url
        self.attr = attr

    def get_attr_values(self):
        """Get song attributes

        Parameters
            None

        Return
            Song attributes values as a list
        """
        return [value for value in self.attr.values()]

class KHAlbum(object):
    """KHAlbum describe a KHinsider album content

    Attributes
        url (str) : KHinsider album URL
        output (str) : Output directory for downloadable content (Default is execution directory) [optional]
        verbose (boolean) : Verbosity boolean to display more informations (Default is 'False') [optional]
    """

    def __init__(self, url, output='.', verbose=False):
        """KHAlbum init

        Raise
            ValueError :
                - If the URL is not valid
                - If output is not a directory
                - If KHinsider album content is not found
        """
        if not url.startswith("https://downloads.khinsider.com/game-soundtracks/album/"):
            raise ValueError(f"'{url}' is not a valid KHinsider URL")

        if not os.path.isdir(output):
            raise ValueError(f"'{output}' is not a directory")

        self.url = url
        self.output = output + '/' if not output.endswith('/') else output
        self.verbose = verbose
        self.album = self.__scrape_album_content()
        self.headers, self.songlist, self.footers = self.__get_songlist_content()

    def __scrape_album_content(self):
        """Scrape album content

        Parameters
            None

        Return
            A soup object representing album content

        Raise
            ValueError if the album content is not found
        """
        html = get_html_from_url(self.url)
        soup = BeautifulSoup(html, 'html.parser')

        # Relevant album informations are in a div tag 'EchoTopic'
        album = soup.find(id='EchoTopic')
        if album is None:
            raise ValueError("The album has no content!")

        return album

    def __get_songlist_content(self):
        """Get song list content

        Parameters
            None

        Return
            A tuple composed of:
                - A list of strings representing song list headers
                - A soup object representing song list content
                - A list of strings representing song list footers

        Raise
            ValueError if the song list content is not found
        """
        # Relevant song list informations are in a table with ID "songlist"
        songlist = self.album.find('table', id='songlist')
        if songlist is None:
            raise ValueError("The album content does not have any song list!")

        headers = [th.get_text(strip=True) for th in songlist.find('tr', id='songlist_header').find_all('th')]
        footers = [th.get_text(strip=True) for th in songlist.find('tr', id='songlist_footer').find_all('th')]

        return (headers, songlist, footers)

    def __strfdelta(self, tdelta, fmt):
        """Format a timedelta object with 'days', 'hours', 'min' and 'sec' placeholders

        Parameters
            tdelta (timedelta object) : timedelta object to format
            fmt (str) : String to format

        Return
            A formatted timedelta object as a string
        """
        d = {"days": tdelta.days}
        d["hours"], rem = divmod(tdelta.seconds, 3600)
        d["min"], d["sec"] = divmod(rem, 60)
        return fmt.format(**d)

    def get_name(self):
        """Get the album name

        Parameters
            None

        Return
            A string object representing album name
        """
        return self.album.find('h2').text

    def get_available_formats(self):
        """Get the song list available formats of the album

        Parameters
            None

        Return
            A list of available formats (mp3, flac, ogg, ...)
        """
        formats = self.headers[self.headers.index('Song Name')+1:-1]
        return [fmt.lower() for fmt in formats]

    def get_songlist(self):
        """Get the song list of the album

        Parameters
            None

        Return
            A song list as KHSong objects
        """
        # Change header to match song attributes indexes
        headers = self.headers.copy()
        headers.insert(headers.index('Song Name')+1, 'Duration')
        songlist = []

        # Search song attributes within each relevant row of the song list table
        for tr in self.songlist('tr')[1:-1]:
            attr = collections.OrderedDict()
            url = tr.find('a')['href']
            cells = tr.find_all('td')
            for index, header in enumerate(headers):
                if not header:
                    continue # Skip unrelevant columns
                attr[header.lower()] = cells[index].text

            songlist.append(KHSong(urllib.parse.urljoin(self.url, url), attr))

        return songlist

    def print_songlist(self):
        """Print the song list of the album and its relative informations

        Parameters
            None

        Return
            None
        """
        result = []
        songlist = self.get_songlist()
        #tot_duration = datetime.timedelta()

        # Change header to match song attributes indexes
        headers = self.headers.copy()
        headers.insert(headers.index('Song Name') + 1, 'Duration')
        headers = list(filter(None, headers))

        print(f"{self.get_name()}\n")

        for song in songlist:
            result.append(song.get_attr_values())

            # Calculate duration
            #s = sum(map(lambda x,y : x*int(y), [1,60,3600], reversed(song.attr['duration'].split(':'))))
            #tot_duration += datetime.timedelta(seconds=int(s))

        print(tabulate(result, headers, tablefmt='presto'))

        print(f"\nTotal duration: {self.footers[self.footers.index('Total:')+1]}")
        #print(f"\nTotal duration: {self.__strfdelta(tot_duration, '{days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)')}")
        for index, fmt in enumerate(self.get_available_formats()):
            print(f"{fmt.upper()} total size: {self.footers[self.footers.index('Total:')+2+index]}")

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
            total_time_elapsed += song.download(self.output, self.verbose)

        print(f"Total time elapsed:" + self.__strfdelta(total_time_elapsed, ' {days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)'))

if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(description="Extract song list from a khinsider game URL")
    parser.add_argument('-o', '--output', default='.', help="Directory output (Default is execution directory)")
    parser.add_argument('-v', '--verbose', default=False, action="store_true", help="More informations displayed")
    parser.add_argument('url', help="Khinsider URL")

    args = parser.parse_args()

    # Scrap game song list
    album = KHAlbum(args.url, args.output, args.verbose)
    album.print_songlist()
