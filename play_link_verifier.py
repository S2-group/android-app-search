"""Filter out package names not available in Google Play.

For each package name in input, check if package name is available in
Google Play. If so, print package name to output.

Input and output have each package name on a separate lines.
"""

import argparse
import logging
import requests
import sys
from typing import IO


LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s | [%(levelname)s] %(message)s'
logger = logging.getLogger(__name__)


def parse_cmdline_arguments() -> argparse.Namespace:
    """Define and parse commandline arguments."""
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--input', default=sys.stdin,
            type=argparse.FileType('r'),
            help='File to read package names from. Default: stdin.')
    arguments.add_argument('--output', default=sys.stdout,
            type=argparse.FileType('w'),
            help='Output file. Default: stdout.')
    arguments.add_argument('--log', default=sys.stderr,
            type=argparse.FileType('w'),
            help='Log file. Default: stderr.')
    return arguments.parse_args()


def is_package_in_play(package_name: str) -> bool:
    """Test if package_name is available in Google Play.

    :param str package_name: Package name to search for in Google Play.
    :returns bool: True if package name is available in Google Play,
        False otherwise.
    """
    response = requests.head(
            'https://play.google.com/store/apps/details',
            params={ 'id': package_name })

    log_msg = 'Status {} for {}'.format(
            response.status_code, response.url)
    if response.status_code != 200 and response.status_code != 404:
        logger.error(log_msg)
    else:
        logger.info(log_msg)

    return response.status_code == 200


def package_filter(input_file: IO[str], output_file: IO[str]):
    """Filter out lines if they do not exist in Google Play.

    :param IO[str] input_file: File to read lines from. Each line is
        considered a package name to test.
    :param IO[str] output_file: File to write package names to if they
        pass the filter.
    """
    for line in input_file.readlines():
        package = line.strip()
        if is_package_in_play(package):
            print(package, file=output_file)


def set_logging_handler(handler: logging.Handler):
    logger.setLevel(handler.level)
    logger.addHandler(handler)


def configure_logger(stream: IO[str]):
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(LOG_LEVEL)

    set_logging_handler(handler)


if __name__ == '__main__':
    args = parse_cmdline_arguments()
    configure_logger(args.log)
    package_filter(args.input, args.output)
