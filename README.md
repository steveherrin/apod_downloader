Astronomy Photo of the Day Downloader
=====================================

This is a quick script I threw together to download Astronomy
Photos of the Day from NASA. I use the images for a screensaver.

See: https://apod.nasa.gov/apod/astropix.html

It should work with both Python 2 and 3.


Requirements
------------

The script has [PEP-723](https://peps.python.org/pep-0723/) annotations,
so this step is not necessary if you are using a tool like
[uv](https://docs.astral.sh/uv/) that supports running scripts directly.

If your tooling does not support inline script metadata, you can install
the required dependencies with:

    pip install -r requirements.txt

I'd suggest installing these in a virtual environment


Usage
-----

First, create a destination directory to hold the photos.

Then run:

    uv run apod_downloader.py <destination>

    # or if you have the dependencies on your python path
    apod_downloader.py <destination>

By default, it downloads the past 30 days. If you want to download
more than 30 days:

    apod_downloader.py <destination> --n-days=90

And by default, it will not touch files in the destination directory.
An optional flag will clear old photos older than the --n-days you
specify:

    apod_downloader.py <destination> --delete-old
