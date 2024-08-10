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

from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import timedelta
from urllib.parse import urljoin, unquote

from bs4 import BeautifulSoup, Tag
from progressbar import DataTransferBar
from requests import get as reqget
from requests.utils import requote_uri
from tabulate import tabulate


def strfdelta(tdelta:timedelta, fmt:str) -> str:
    """Formats a timedelta object with 'days', 'hours', 'min' and 'sec' placeholders

    Arguments:
        tdelta (timedelta): The timedelta object to format
        fmt (str): The string to use

    Returns:
        A formatted timedelta object as a string
    """
    data = {'days': tdelta.days}
    data['hours'], rem = divmod(tdelta.seconds, 3600)
    data['min'], data['sec'] = divmod(rem, 60)

    return fmt.format(**data)

def query_yes_no(question:str, default:str='yes') -> bool:
    """Prompts the user for a boolean choice

    Arguments:
        question (str): The question to ask to the user
        default (str): The default answer (Default is 'yes') [optional]

    Raises:
        ValueError: The default answer is invalid

    Returns
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
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError(f'Invalid default value: "{default}"')

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        if choice in valid:
            return valid[choice]

class KHFile():
    """The KHFile class defines utilities to download KHinsider files

    Attributes:
        pbar (DataTransferBar): The file progress bar
    """

    def __init__(self) -> None:
        """KHFile initializer"""
        self.pbar = None

    def __update_progress_bar(self, count:int, block_size:int, total_size:int) -> None:
        """Initializes and updates the progress bar

        Arguments:
            count (int): The block number
            block_size (int): The maximum size blocks that are read in
            total_size (int): The total size of the download
        """
        if self.pbar is None:
            self.pbar = DataTransferBar(max_value=total_size)

        downloaded = count * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()

    def download_file(self, url:str, file:str, timeout:float=None, chunk_size:int=1024) -> timedelta:
        """Downloads the file at a given URL and updates its progress bar

        Arguments:
            url (str): The URL to look for
            file (str) : The targeted path and name of the file
            timeout (float) : The inactivity timeout in seconds (Default is None) [optional]
            chunk_size (int) : The number of bytes to read into memory (Default is 1024) [optional]

        Returns:
            The time elapsed to download the file as a timedelta object
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
                self.__update_progress_bar(index + 1, chunk_size, file_size)

        # Reset progress bar
        time_elapsed = self.pbar.data()['time_elapsed']
        self.pbar = None

        return time_elapsed

class KHCover(KHFile):
    """The KHCover class describes a KHinsider cover

    Attributes:
        url (str): The URL of the KHinsider cover
    """

    def __init__(self, url):
        """KHCover initializer"""
        super().__init__()
        self.url = url

    def download(self, output:str='.', timeout:float=None, chunk_size:int=1024, verbose:bool=False) -> timedelta:
        """Downloads the cover to an output directory

        Arguments:
            output (str) : Output directory (Default is execution directory) [optional]
            timeout (float) : Inactivity timeout in seconds [optional]
            chunk_size (int) : Number of bytes to read into memory (Default is 1024) [optional]
            verbose (boolean) : Verbosity boolean to display more informations (Default is 'False') [optional]

        Returns:
            The time elapsed to download the cover as a timedelta object
        """
        if verbose:
            print('Cover link: ' + self.url)

        # Download cover to output directory
        file = os.path.basename(unquote(self.url))
        return self.download_file(self.url, os.path.join(output, file), timeout, chunk_size)

class KHSong(KHFile):
    """The KHSong class describes a KHinsider song

    Attributes:
        url (str): The URL of the KHinsider song
        attr (dict[str,str]): The song attributes (name, duration, formats ...)
    """

    def __init__(self, url:str, attr:dict[str,str]) -> None:
        """KHSong initializer"""
        super().__init__()
        self.url = url
        self.attr = attr

    def __get_download_links(self, timeout:float=None) -> list[str]:
        """Gets the song download links for each available format

        Arguments:
            timeout (float): The inactivity timeout in seconds [optional]

        Returns:
            A list of strings representing download links
        """
        html = reqget(self.url, timeout=timeout).text
        soup = BeautifulSoup(html, 'html.parser')

        # Relevants links have a nested "Click here [...]" span
        return [span.parent['href'] for span in soup.find_all('span') if span.parent.name == 'a' and 'Click here' in span.text]

    def get_attr_values(self) -> list[str]:
        """Gets the song attribute values

        Returns:
            The song attribute values as a list
        """
        return list(self.attr.values())

    def download(self, output:str='.', fmt:str='mp3', timeout:float=None, chunk_size:int=1024, verbose:bool=False) -> timedelta:
        """Downloads the song with a given format to an output directory

        Arguments:
            output (str): The output directory (Default is execution directory) [optional]
            fmt (str): The download format (mp3, flac, ogg, ...) (Default is mp3) [optional]
            timeout (float): The inactivity timeout in seconds [optional]
            chunk_size (int): The number of bytes to read into memory (Default is 1024) [optional]
            verbose (bool): The verbosity boolean to display more informations (Default is 'False') [optional]

        Raises:
            ValueError: The requested format is not available

        Returns:
            The time elapsed to download the song as a timedelta object
        """
        links = self.__get_download_links(timeout=timeout)

        for link in links:
            if os.path.splitext(link)[1][1:] == fmt:
                if verbose:
                    print('Song link: ' + link)

                # Download song with given format to output directory
                file = os.path.basename(unquote(link))
                return self.download_file(link, os.path.join(output, file), timeout, chunk_size)

        raise ValueError(f'{fmt.upper()} format not found for "{self.attr['song name']}" song')

class KHAlbum():
    """The KHAlbum class describes a KHinsider album

    Attributes:
        url (str): URL of the KHinsider album
        album (Tag): Navigable HTML album content
        headers (list[str]): A list of strings representing tracklist headers
        tracklist (Tag): Navigable HTML tracklist content
        footers (list[str]): A list of strings representing tracklist footers
    """

    def __init__(self, url:str) -> None:
        """KHAlbum initializer

        Arguments:
            url (str) : The URL of the KHinsider album

        Raises:
            ValueError: The URL is not valid or an HTML scrape error occurred
        """
        if not url.startswith('https://downloads.khinsider.com/game-soundtracks/album/'):
            raise ValueError(f'"{url}" is not a valid KHinsider album URL')

        self.url = url
        self.album = self.__get_html_content()
        self.headers, self.tracklist, self.footers = self.__get_tracklist()

    def __get_html_content(self) -> Tag:
        """Gets the album HTML content

        Returns:
            A navigable HTML content as a Tag

        Raises:
            ValueError: The album content could not be found
        """
        html = reqget(self.url, timeout=5).text
        soup = BeautifulSoup(html, 'html.parser')

        # Relevant album content is in a div tag 'PageContent'
        content = soup.find('div', id='pageContent')
        if content is None:
            raise ValueError('The album content could not be found')

        return content

    def __get_tracklist(self) -> tuple[list[str], Tag, list[str]]:
        """Gets the tracklist of the album

        Raises:
            ValueError: The tracklist content could not be found

        Returns:
            A tuple composed of:
                - A list of strings representing tracklist headers
                - A navigable tracklist content as a Tag
                - A list of strings representing tracklist footers
        """
        # Relevant tracklist content is in a table with ID 'songlist'
        tracklist = self.album.find('table', id='songlist')
        if tracklist is None:
            raise ValueError('The tracklist content could not be found')

        # Change headers to match song attributes indexes
        headers = [th.get_text(strip=True) for th in tracklist.find('tr', id='songlist_header').find_all('th')]
        headers.insert(headers.index('Song Name')+1, 'Duration')

        footers = [th.get_text(strip=True) for th in tracklist.find('tr', id='songlist_footer').find_all('th')]

        return (headers, tracklist, footers)

    def get_name(self) -> str:
        """Gets the album name

        Returns:
            A string representing album name
        """
        return self.album.find('h2').text

    def get_available_formats(self) -> list[str]:
        """Gets the available formats of the album

        Returns:
            A list of strings representing available formats (mp3, flac, ogg, ...)
        """
        formats = self.headers[self.headers.index('Duration')+1:-2]
        return [fmt.lower() for fmt in formats]

    def get_covers(self) -> list[KHCover]:
        """Gets the covers of the album

        Returns:
            A list of KHCover objects
        """
        # Relevant covers are in a div with class 'albumImage'
        return [KHCover(requote_uri(div.find('a')['href'])) for div in self.album.find_all('div', class_='albumImage')]

    def get_tracklist(self) -> list[KHSong]:
        """Gets the tracklist of the album

        Returns:
            A list of KHSong objects
        """
        tracklist = []

        # Search song attributes within each relevant row of the tracklist content
        for row in self.tracklist('tr')[1:-1]:
            attr = {}
            url = requote_uri(row.find('a')['href'])
            cells = row.find_all('td')

            for index, header in enumerate(self.headers):
                if not header:
                    continue # Skip unrelevant columns
                attr[header.lower()] = cells[index].text

            tracklist.append(KHSong(urljoin(self.url, url), attr))

        return tracklist

    def print(self) -> None:
        """Prints the album metadata"""
        result = []
        tracklist = self.get_tracklist()
        total = timedelta()

        # Eliminate empty headers
        headers = [header for header in self.headers if header]

        print(f'{self.get_name()}\n')

        for song in tracklist:
            result.append(song.get_attr_values())

            # Calculate duration in seconds
            sec = sum(map(lambda x,y : x * int(y), [1,60,3600], reversed(song.attr['duration'].split(':'))))
            total += timedelta(seconds=int(sec))

        print(tabulate(result, headers, tablefmt='presto'))

        # We could retrieve the total duration in the footer, but we want to pretify it easily
        print(f'\nTotal duration: {strfdelta(total, '{days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)')}')

        for index, fmt in enumerate(self.get_available_formats()):
            print(f'{fmt.upper()} total size: {self.footers[self.footers.index('Total:') + 2 + index]}')

        print(f'Number of covers: {len(self.get_covers())}')

    def download(self, output:str='.', fmt:str='mp3', timeout:float=None, chunk_size:int=1024, start:int=None, end:int=None, dlcovers:bool=False, verbose:bool=False) -> None:
        """Downloads the tracklist of the album with a given format to an output directory

        Arguments:
            output (str): The output directory (Default is execution directory) [optional]
            fmt (str): The download format (mp3, flac, ogg, ...) (Default is mp3) [optional]
            timeout (float): The inativity timeout in seconds for downloading a cover/song (Default is None) [optional]
            chunk_size (int): The number of bytes to read into memory (Default is 1024) [optional]
            start (int): The start download at a given included index in the tracklist (Default is None) [optional]
            end (int): The end download at a given included index in the tracklist (Default is None) [optional]
            dlcovers (bool): Download covers or not (Default is False) [optional]
            verbose (bool): Display more informations or not (Default is 'False') [optional]

        Raises:
            ValueError: The output is not a directory or the start/end indexes are invalid
        """
        covers = self.get_covers()
        tracklist = self.get_tracklist()
        total = timedelta()

        # Check consistency
        if not os.path.isdir(output):
            raise ValueError(f'"{output}" is not a valid directory')

        if start and (start < 0 or start > len(tracklist)):
            raise ValueError(f'The start index "{start}" is invalid')

        if end and (end < 0 or end > len(tracklist)):
            raise ValueError(f'The end index "{end}" is invalid')

        if start and end and start > end:
            raise ValueError(f'The start index "{start}" cannot exceed the end index "{end}"')

        # Download covers of the album
        if dlcovers:
            for index, cover in enumerate(covers):
                print(f'Downloading cover [{index+1}/{len(covers)}]...')
                total += cover.download(output, timeout, chunk_size, verbose)

        # Download the tracklist of the album
        for index, song in enumerate(tracklist):
            # Skip if below the start index
            if start and index+1 < start:
                continue

            # Break if higher than the end index
            if end and index+1 > end:
                break

            if end:
                print(f'Downloading "{song.attr['song name']}" [{index+1}/{end}]...')
            else:
                print(f'Downloading "{song.attr['song name']}" [{index+1}/{len(tracklist)}]...')

            total += song.download(output, fmt, timeout, chunk_size, verbose)

        print('Total time elapsed:' + strfdelta(total, ' {days} day(s) {hours} hour(s) {min} min(s) {sec} sec(s)'))

if __name__ == "__main__":

    # Parse arguments
    parser = ArgumentParser(description='Download tracklist from a KHinsider album URL', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-o', '--output', default='.', help='Choose output directory (Default is execution directory)')
    parser.add_argument('-f', '--format', default='mp3', help='Choose download format (Default is MP3)')
    parser.add_argument('-t', '--timeout', default=None, type=float, help='Set inactivity timeout in seconds (Default is None)')
    parser.add_argument('--chunk', default=1024, type=int, metavar='CHUNK_SIZE',
        help="Set chunk size in bytes for covers/songs download.\nDo not touch if you don't know what you're doing (Default is 1024)")
    parser.add_argument('--start', default=None, type=int, help='Choose start index in the album tracklist (Default is None)')
    parser.add_argument('--end', default=None, type=int, help='Choose end index in the album tracklist (Default is None)')
    parser.add_argument('-c', '--covers', default=False, action='store_true', help='Download covers (Default is False)')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Enable verbose mode (Default is False)')
    parser.add_argument('url', help='KHinsider album URL')

    args = parser.parse_args()
    album = KHAlbum(args.url)

    # Check consistency
    if args.format.lower() not in album.get_available_formats():
        raise ValueError(f'{args.format.upper()} not available for "{album.get_name()}" album')

    # Print album informations
    album.print()

    print(f'\nChosen format: {args.format.upper()}')
    print(f'Chosen directory: {args.output}')
    if args.timeout:
        print(f'Chosen timeout: {args.timeout} sec.')
    print(f'Chosen chunk size: {args.chunk} bytes')
    if args.start:
        print(f'Chosen start index: {args.start}')
    if args.end:
        print(f'Chosen end index: {args.end}')
    print(f'Download covers: {args.covers}')

    if not query_yes_no('\nIs this ok ?', 'yes'):
        sys.exit(1)

    # Download album tracklist
    album.download(args.output, args.format.lower(), args.timeout, args.chunk, args.start, args.end, args.covers, args.verbose)
