#!/usr/bin/env python

from __future__ import print_function, unicode_literals
import argparse
from bs4 import BeautifulSoup
import datetime
import os
import requests
import six
from six.moves.urllib.parse import urljoin, urlparse
import sys


IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
URL_FORMAT = 'https://apod.nasa.gov/apod/ap%y%m%d.html'
LOCAL_DATE_FORMAT = '%Y-%m-%d'


class DownloaderError(Exception):
    pass


def is_image(url):
    return any(url.endswith(extension) for extension in IMAGE_EXTENSIONS)


def _get_requests_session():
    """
    Get a requests session with some retry logic set

    This is needed since I've been getting 'connection reset by peer'
    errors consistently. Possibly some rate limiting?
    """
    retry = requests.packages.urllib3.util.retry.Retry(
        total=3,
        backoff_factor=10,
        status_forcelist=[429,]  # just in case they start using this
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    sess = requests.Session()
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess


def image_url_for_date(requests_session, date):
    url = date.strftime(URL_FORMAT)
    r = requests_session.get(url)
    if r.status_code != 200:
        raise DownloaderError("Fetching '{}' failed: {}".format(url, r.status_code))
    parser = BeautifulSoup(r.text, 'html.parser')
    for link in parser.center.find_all('a'):
        href = link.get('href')
        if is_image(href):
            return urljoin(url, href)
    raise DownloaderError("Could not find an image for {}".format(date))


def date_name(old_name, date):
    extension = old_name.split('.')[-1]
    date_str = date.strftime(LOCAL_DATE_FORMAT)
    return '.'.join((date_str, extension))


def download_image_for_date(requests_session, date, destination_dir):
    url = image_url_for_date(requests_session, date)
    original_name = urlparse(url).path.split('/')[-1]
    dest_name = date_name(original_name, date)

    dest_path = os.path.join(destination_dir, dest_name)
    if os.path.exists(dest_path):
        return  # already downloaded
    r = requests_session.get(url)
    if r.status_code != 200:
        raise DownloaderError("Could not download '{}': {}".format(url, r.status_code))
    with open(dest_path, 'wb') as f:
        f.write(r.content)


def download_photos(n_days, destination_dir):
    if not os.path.isdir(destination_dir):
        raise ValueError("'{}' is not a valid directory".format(destination_dir))

    requests_session = _get_requests_session()

    today = datetime.date.today()
    for i in six.moves.xrange(n_days):
        date = today - datetime.timedelta(days=i)

        try:
            download_image_for_date(requests_session, date, destination_dir)
        except DownloaderError:
            print("Couldn't get image for {}".format(date), file=sys.stderr)


def clear_old_photos(n_days, destination_dir):
    oldest = datetime.date.today() - datetime.timedelta(days=n_days)
    for file_name in os.listdir(destination_dir):
        try:
            date = datetime.datetime.strptime(file_name.split('.')[0], LOCAL_DATE_FORMAT).date()
        except ValueError:
            continue # some file that doesn't fit the naming scheme; ignore it
        if date < oldest:
            os.remove(os.path.join(destination_dir, file_name))


def main(n_days, destination_dir, delete_old):
    download_photos(n_days, destination_dir)
    if delete_old:
        clear_old_photos(n_days, destination_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download recent NASA Astronomy Photos of the Day')
    parser.add_argument('destination', type=str,
                        help='directory to put the downloaded photos in')
    parser.add_argument('-n', '--n-days', dest='n_days', type=int, default=30,
                        help='number of days to download')
    parser.add_argument('--delete-old', dest='delete_old', action='store_true',
                        help='delete photos older than the number of days specified')

    args = parser.parse_args()

    main(args.n_days, args.destination, args.delete_old)
