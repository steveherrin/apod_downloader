Astronomy Photo of the Day Downloader
=====================================

This is a quick script I threw together to download Astronomy
Photos of the Day from NASA.

See: https://apod.nasa.gov/apod/astropix.html

It should work with both Python 2 and 3.


Requirements
------------

You can install any required packages with

    pip install -r requirements.txt

I'd suggest installing these in a virtual environment


Usage
-----

First, create a destination directory to hold the photos.

Then run:

    apod_downloader.py <destination>

By default, it downloads the past 30 days. If you want to download
more than 30 days:

	apod_downloader.py <destination> --n-days=90

And by default, it will not touch files in the destination directory.
An optional flag will clear old photos older than the --n-days you
specify:

	apod_downloader.py <destination> --delete-old
