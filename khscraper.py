# -*- coding: utf-8 -*-
"""
khinsider scraping tool
"""
#
# Copyright (c) 2020, Marc GIANNETTI <mgtti.pro@gmail.com>
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
#  - Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
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
from datetime import timedelta
from collections import OrderedDict
from urllib.parse import urljoin, unquote
from argparse import ArgumentParser, RawTextHelpFormatter

from requests import get as reqget # requests package
from requests.utils import requote_uri # requests package
from progressbar import DataTransferBar # progressbar2 package
from bs4 import BeautifulSoup # beautifulsoup4 package
from tabulate import tabulate # tabulate package

def get_html_from_url(url, timeout=None):
    """Get HTML document from URL

    Parameters
        url (str) : URL to look for
        timeout (float) : Inactivity timeout in seconds

    Return
        The HTML document as a string
    """

    resp = reqget(url, timeout=timeout)
    return resp.text

def strfdelta(tdelta, fmt):
    """Format a timedelta object with 'days', 'hours', 'min' and 'sec' placeholders

    Parameters
        tdelta (datetime.timedelta) : timedelta object to format
        fmt (str) : String to format

    Return
        A formatted timedelta object as a string
    """
    data = {"days": tdelta.days}
    data["hours"], rem = divmod(tdelta.seconds, 3600)
    data["min"], data["sec"] = divmod(rem, 60)
    return fmt.format(**data)

def query_yes_no(question, default='yes'):
    """Prompt user for a boolean choice

    Parameters
        question (str) : Question to ask to user
        default (str) : Default answer (Default is 'yes') [optional]

    Return
        A boolean representing user choice

    Raise
        ValueError if the default answer is invalid
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
        if choice in valid:
            return valid[choice]

class KHFile():
    """KHFile defines utilities to download KHinsider files

    Attributes
        None
    """
    def __init__(self):
        """KHFile init"""
        self.pbar = None

    def __update_progress_bar(self, count, block_size, total_size):
        """Initialize/Update progress bar

        Parameters
            count (int) : Block number
            block_size (int) : Maximum size blocks that are read in
            total_size (int) : Total size of the download

        Return
            None
        """
        if self.pbar is None:
            self.pbar = DataTransferBar(max_value=total_size)

        downloaded = count * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()

    def download_file(self, url, file, timeout=None, chunk_size=1024):
        """Download a file at a given URL & update progress bar

        Parameters
            url (str) : URL to look for
            file (str) : Targeted path and name of the file
            timeout (float) : Inactivity timeout in seconds (Default is None) [optional]
            chunk_size (int) : Number of bytes to read into memory (Default is 1024) [optional]

        Return
            The time elapsed to download file as a timedelta object
        """
        with reqget(url, timeout=timeout, stream=True) as resp:
            # Retrieve file size
            file_size = int(resp.headers['Content-Length'].strip())

            with open(file, 'wb') as sav:
                index = 0
                for index, chunk in enumerate(resp.iter_content(chunk_size)):
                    # Write chunk to file & update progress bar
                    sav.write(chunk)
                    self.__update_progress_bar(index, chunk_size, file_size)

                # Finish progress bar
                self.__update_progress_bar(index+1, chunk_size, file_size)

        # Reset progress bar
        time_elapsed = self.pbar.data()['time_elapsed']
        self.pbar = None

        return time_elapsed

class KHCover(KHFile):
    """KHCover describe a KHinsider cover

    Attributes
        url (str) : KHinsider cover URL
    """

    def __init__(self, url):
        """KHCover init

        Raise
            ValueError if the URL is not valid
        """
        super().__init__()

        if not url.startswith("https://vgmsite.com/soundtracks/"):
            raise ValueError(f"'{url}' is not a valid KHinsider cover URL")

        self.url = url

    def download(self, output='.', timeout=None, chunk_size=1024, verbose=False):
        """Download a cover to output directory

        Parameters
            output (str) : Output directory (Default is execution directory) [optional]
            timeout (float) : Inactivity timeout in seconds [optional]
            chunk_size (int) : Number of bytes to read into memory (Default is 1024) [optional]
            verbose (boolean) : Verbosity boolean to display more informations (Default is 'False') [optional]

        Return
            The time elapsed to download cover as a timedelta object
        """
        if verbose:
            print("Link found: " + self.url)

        # Download cover to output directory
        file = os.path.basename(unquote(self.url))
        return self.download_file(self.url, os.path.join(output, file), timeout, chunk_size)

class KHSong(KHFile):
    """KHSong describe a KHinsider song

    Attributes
        url (str) : KHinsider song URL
        attr (OrderDict) : Song attributes (name, duration, formats ...)
    """

    def __init__(self, url, attr):
        """KHSong init

        Raise
            ValueError if the URL is not valid
        """
        super().__init__()

        if not url.startswith("https://downloads.khinsider.com/game-soundtracks/album/"):
            raise ValueError(f"'{url}' is not a valid KHinsider song URL")

        self.url = url
        self.attr = attr

    def __get_download_links(self, timeout=None):
        """Get song download links for each available format

        Parameters
            timeout (float) : Inactivity timeout in seconds [optional]

        Return
            A list of strings representing download links
        """
        html = get_html_from_url(self.url, timeout=timeout)
        soup = BeautifulSoup(html, 'html.parser')

        # Relevant download links are hosted on "vgmsite"
        links = [anchor['href'] for anchor in soup.find_all('a', href=re.compile(r'^https://vgmsite.com'))]
        return links

    def get_attr_values(self):
        """Get song attributes

        Parameters
            None

        Return
            Song attributes values as a list
        """
        return list(self.attr.values())

    def download(self, output='.', fmt='mp3', timeout=None, chunk_size=1024, verbose=False):
        """Download a song with a given format to output directory

        Parameters
            output (str) : Output directory (Default is execution directory) [optional]
            fmt (str) : Download format (mp3, flac, ogg, ...) (Default is mp3) [optional]
            timeout (float) : Inactivity timeout in seconds [optional]
            chunk_size (int) : Number of bytes to read into memory (Default is 1024) [optional]
            verbose (boolean) : Verbosity boolean to display more informations (Default is 'False') [optional]

        Return
            The time elapsed to download song as a timedelta object

        Raise
            ValueError if the requested format is not available
        """
        links = self.__get_download_links(timeout=timeout)

        for link in links:
            if os.path.splitext(link)[1][1:] == fmt:
                if verbose:
                    print("Link found: " + link)

                # Download song with given format to output directory
                file = os.path.basename(unquote(link))
                return self.download_file(link, os.path.join(output, file), timeout, chunk_size)

        raise ValueError(f"{fmt.upper()} format not found for '{self.attr['song name']}' song")

class KHAlbum():
    """KHAlbum describe a KHinsider album content

    Attributes
        url (str) : KHinsider album URL
    """

    def __init__(self, url):
        """KHAlbum init

        Raise
            ValueError :
                - If the URL is not valid
                - If KHinsider album content is not found
        """
        if not url.startswith("https://downloads.khinsider.com/game-soundtracks/album/"):
            raise ValueError(f"'{url}' is not a valid KHinsider album URL")

        self.url = url
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

        # Relevant album content are in a div tag 'PageContent'
        content = soup.find(id='pageContent')
        if content is None:
            raise ValueError("The album has no content!")

        return content

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

        # Change headers to match song attributes indexes
        headers = [th.get_text(strip=True) for th in songlist.find('tr', id='songlist_header').find_all('th')]
        headers.insert(headers.index('Song Name')+1, 'Duration')

        footers = [th.get_text(strip=True) for th in songlist.find('tr', id='songlist_footer').find_all('th')]

        return (headers, songlist, footers)

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
            A list of strings representing available formats (mp3, flac, ogg, ...)
        """
        formats = self.headers[self.headers.index('Duration')+1:-1]
        return [fmt.lower() for fmt in formats]

    def get_covers(self):
        """Get the album covers

        Parameters
            None

        Return
            A cover list as KHCover objects
        """
        # Relevant covers are hosted on "vgmsite"
        covers = [KHCover(requote_uri(anchor['href'])) for anchor in self.album.find_all('a', href=re.compile(r'^https://vgmsite.com'))]
        return covers

    def get_songlist(self):
        """Get the song list of the album

        Parameters
            None

        Return
            A song list as KHSong objects
        """
        songlist = []

        # Search song attributes within each relevant row of the song list table
        for row in self.songlist('tr')[1:-1]:
            attr = OrderedDict()
            url = requote_uri(row.find('a')['href'])
            cells = row.find_all('td')
            for index, header in enumerate(self.headers):
                if not header:
                    continue # Skip unrelevant columns
                attr[header.lower()] = cells[index].text

            songlist.append(KHSong(urljoin(self.url, url), attr))

        return songlist

    def print(self):
        """Print the album name, its songlist and misc informations

        Parameters
            None

        Return
            None
        """
        result = []
        songlist = self.get_songlist()
        tot_duration = timedelta()

        # Eliminate empty headers
        headers = [header for header in self.headers if header]

        print(f"{self.get_name()}\n")

        for song in songlist:
            result.append(song.get_attr_values())

            # Calculate duration in seconds
            sec = sum(map(lambda x,y : x*int(y), [1,60,3600], reversed(song.attr['duration'].split(':'))))
            tot_duration += timedelta(seconds=int(sec))

        print(tabulate(result, headers, tablefmt='presto'))

        # We could retrieve the total duration in the footer, but we want to pretify it easily
        print(f"\nTotal duration: {strfdelta(tot_duration, '{days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)')}")
        for index, fmt in enumerate(self.get_available_formats()):
            print(f"{fmt.upper()} total size: {self.footers[self.footers.index('Total:')+2+index]}")
        print(f"Number of covers: {len(self.get_covers())}")

    def download(self, output='.', fmt='mp3', timeout=None, chunk_size=1024, start=None, end=None, dlcovers=False, verbose=False):
        """Download the song list of the album with a given format to output directory

        Parameters
            output (str) : Output directory (Default is execution directory) [optional]
            fmt (str) : Download format (mp3, flac, ogg, ...) (Default is mp3) [optional]
            timeout (float) : Inactivity timeout in seconds (Default is None) [optional]
            chunk_size (int) : Number of bytes to read into memory (Default is 1024) [optional]
            start (int) : Start download at a given included index in the song list (Default is None) [optional]
            end (int) : End download at a given included index in the song list (Default is None) [optional]
            dlcovers (boolean) : Download covers (Default is False) [optional]
            verbose (boolean) : Verbosity boolean to display more informations (Default is 'False') [optional]

        Return
            None

        Raise
            ValueError if:
                - The output is not a directory
                - The start or end index(es) are invalid
        """
        covers = self.get_covers()
        songlist = self.get_songlist()
        total_time_elapsed = timedelta()

        # Check consistency
        if not os.path.isdir(output):
            raise ValueError(f"'{output}' is not a valid directory")

        if start and (start < 0 or start > len(songlist)):
            raise ValueError(f"The start index '{start}' is invalid")

        if end and (end < 0 or end > len(songlist)):
            raise ValueError(f"The end index '{end}' is invalid")

        if start and end and start > end:
            raise ValueError(f"The start index '{start}' is higher than the end index '{end}'")

        # Download covers of the album
        if dlcovers:
            for index, cover in enumerate(covers):
                print(f"Downloading cover [{index+1}/{len(covers)}]...")
                total_time_elapsed += cover.download(output, timeout, chunk_size, verbose)

        # Download the song list of the album
        for index, song in enumerate(songlist):
            # Skip if below the start index
            if start and index+1 < start:
                continue

            # Break if higher than the end index
            if end and index+1 > end:
                break

            if end:
                print(f"Downloading '{song.attr['song name']}' [{index+1}/{end}]...")
            else:
                print(f"Downloading '{song.attr['song name']}' [{index+1}/{len(songlist)}]...")
            total_time_elapsed += song.download(output, fmt, timeout, chunk_size, verbose)

        print("Total time elapsed:" + strfdelta(total_time_elapsed, ' {days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)'))

if __name__ == "__main__":
    # Parse arguments
    parser = ArgumentParser(description="Download song list from a KHinsider album URL", formatter_class=RawTextHelpFormatter)
    parser.add_argument('-o', '--output', default='.', help="Choose output directory (Default is execution directory)")
    parser.add_argument('-f', '--format', default='mp3', help="Choose download format (Default is MP3)")
    parser.add_argument('-t', '--timeout', default=None, type=float, help="Set inactivity timeout in seconds (Default is None)")
    parser.add_argument('--chunk', default=1024, type=int, metavar='CHUNK_SIZE',
        help="Set chunk size in bytes for covers/songs download.\nDo not touch if you don't know what you're doing (Default is 1024)")
    parser.add_argument('--start', default=None, type=int, help="Choose start index in the album song list (Default is None)")
    parser.add_argument('--end', default=None, type=int, help="Choose end index in the album song list (Default is None)")
    parser.add_argument('-c', '--covers', default=False, action="store_true", help="Download covers (Default is False)")
    parser.add_argument('-v', '--verbose', default=False, action="store_true", help="Enable verbose mode (Default is False)")
    parser.add_argument('url', help="KHinsider album URL")

    args = parser.parse_args()
    album = KHAlbum(args.url)

    # Check consistency
    if args.format.lower() not in album.get_available_formats():
        raise ValueError(f"{args.format.upper()} not available for '{album.get_name()}' album")

    # Print album informations
    album.print()
    print(f"\nChosen format: {args.format.upper()}")
    print(f"Chosen directory: {args.output}")
    if args.timeout:
        print(f"Chosen timeout: {args.timeout} sec.")
    print(f"Chosen chunk size: {args.chunk} bytes")
    if args.start:
        print(f"Chosen start index: {args.start}")
    if args.end:
        print(f"Chosen end index: {args.end}")
    print(f"Download covers: {args.covers}")

    if not query_yes_no("\nIs this ok ?", 'yes'):
        sys.exit(1)

    # Download album song list
    album.download(args.output, args.format.lower(), args.timeout, args.chunk, args.start, args.end, args.covers, args.verbose)
