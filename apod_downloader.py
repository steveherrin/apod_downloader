#!/usr/bin/env python
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "beautifulsoup4>=4.12.0",
#     "requests>=2.31.0",
#     "six>=1.16.0",
# ]
# ///

from __future__ import print_function, unicode_literals
import argparse
from bs4 import BeautifulSoup
import datetime
import os
import re
import requests
import six
from six.moves.urllib.parse import urljoin, urlparse
import sys


IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
APOD_INDEX_URL = 'https://science.nasa.gov/apod/'
# article slugs vary (/image-article/apod-2026-september-30-...,
# /image-article/apod/apod-..., /image-article/apod-august-4-2026-...)
ARTICLE_URL_RE = re.compile(r'/image-article/(?:[^/]+/)*apod-')
# page titles are consistent: "APOD: 2026 September 30 - ..."
TITLE_DATE_RE = re.compile(r'APOD:\s*(\d{4})\s+([A-Za-z]+)\s+(\d{1,2})\b')
LOCAL_DATE_FORMAT = '%Y-%m-%d'


class DownloaderError(Exception):
    pass


def is_image(url):
    path = urlparse(url).path.lower()
    return any(path.endswith(extension) for extension in IMAGE_EXTENSIONS)


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


def _get_page(requests_session, url):
    r = requests_session.get(url)
    if r.status_code != 200:
        raise DownloaderError("Fetching '{}' failed: {}".format(url, r.status_code))
    return BeautifulSoup(r.text, 'html.parser')


def _hero_links(parser):
    """All links inside the page's main media block"""
    return parser.select('.media-detail-hero__media a[href]')


def date_from_article(parser, page_url):
    title = parser.title.get_text() if parser.title else ''
    match = TITLE_DATE_RE.search(title)
    if not match:
        raise DownloaderError("Could not find a date on '{}'".format(page_url))
    return datetime.datetime.strptime('-'.join(match.groups()), '%Y-%B-%d').date()


def latest_article_url(requests_session):
    parser = _get_page(requests_session, APOD_INDEX_URL)
    # prefer the main image's link; fall back to any APOD article link
    for link in _hero_links(parser) + parser.find_all('a', href=True):
        href = link['href']
        if ARTICLE_URL_RE.search(href):
            return urljoin(APOD_INDEX_URL, href)
    raise DownloaderError("Could not find today's APOD on '{}'".format(APOD_INDEX_URL))


def image_url_from_article(parser, page_url):
    # the query string on these URLs requests the full size; without it the
    # image gets downscaled, so keep it intact
    candidates = [link['href'] for link in _hero_links(parser)]
    # some pages (e.g. before/after rollovers) have no link, just the <img>
    candidates += [img['src'] for img in parser.select('.media-detail-hero__media img[src]')]
    for candidate in candidates:
        url = urljoin(page_url, candidate)
        if is_image(url):
            return url
    return None  # e.g. a video


def prev_article_url(parser, page_url):
    link = parser.select_one('a.smd-next-prev__prev[href]')
    if link is None:
        return None
    return urljoin(page_url, link['href'])


def date_name(old_name, date):
    extension = old_name.split('.')[-1]
    date_str = date.strftime(LOCAL_DATE_FORMAT)
    return '.'.join((date_str, extension))


def download_image(requests_session, url, date, destination_dir):
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

    oldest = datetime.date.today() - datetime.timedelta(days=n_days - 1)
    try:
        url = latest_article_url(requests_session)
    except DownloaderError as e:
        print(e, file=sys.stderr)
        return

    # article URLs can't be derived from dates, so walk the "previous" links
    newer_date = None
    for _ in six.moves.xrange(n_days):
        try:
            parser = _get_page(requests_session, url)
            date = date_from_article(parser, url)
        except DownloaderError as e:
            # without the page there's no link to the previous day
            print(e, file=sys.stderr)
            return
        if date < oldest:
            break
        if newer_date is not None and newer_date - date > datetime.timedelta(days=1):
            # the site's "previous" links occasionally skip a day
            print("Skipped from {} to {}; days in between are not linked".format(
                newer_date, date), file=sys.stderr)
        newer_date = date

        image_url = image_url_from_article(parser, url)
        if image_url is None:
            print("No image for {} (maybe a video?)".format(date), file=sys.stderr)
        else:
            try:
                download_image(requests_session, image_url, date, destination_dir)
            except DownloaderError:
                print("Couldn't get image for {}".format(date), file=sys.stderr)

        url = prev_article_url(parser, url)
        if url is None:
            break


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
