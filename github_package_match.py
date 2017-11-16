"""Match package names to Github repositories.

TODO
"""

import argparse
import csv
import json
import logging
import sys
from typing import List, Tuple
from typing.io import IO

from util.package import Package
from util.parse import parse_package_details, parse_package_to_repos_file


LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s | [%(levelname)s] %(message)s'
logger = logging.getLogger(__name__)


def parse_cmdline_arguments() -> argparse.Namespace:
    """Define and parse commandline arguments."""
    arguments = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument(
        'DETAILS_DIRECTORY',
        type=str,
        help='Directory containing JSON files with details from Google Play.')
    arguments.add_argument(
        '-p', '--package_list',
        default=sys.stdin,
        type=argparse.FileType('r'),
        help='''CSV file that matches package names to repositories.
            The file needs to contain a column `package` and a
            column `all_repos`. `all_repos` contains a comma
            separated string of Github repositories that include an
            AndroidManifest.xml file for package name in column
            `package`. Default: stdin.
            ''')
    arguments.add_argument(
        '-o', '--out', default=sys.stdout, type=argparse.FileType('w'),
        help='File to write CSV output to. Default: stdout')
    arguments.add_argument(
        '--log', default=sys.stderr,
        type=argparse.FileType('w'),
        help='Log file. Default: stderr.')
    return arguments.parse_args()


def set_logging_handler(handler: logging.Handler):
    """Use handler for logging in this module."""
    logger.setLevel(handler.level)
    logger.addHandler(handler)


def configure_logger(stream: IO[str]):
    """Create handler for logging to stream."""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(LOG_LEVEL)
    set_logging_handler(handler)


def match_play_and_github(package_to_repo: IO[str], details_dir: str):
    stats = {
            'all': 0,
            'unknown': 0,
            'valid': 0,
            'no_github_link': 0,
            'unique_repo': 0,
            'no_repo': 0,
            'too_many_repos': 0,
            }
    packages = parse_package_to_repos_file(package_to_repo)

    for package_name, package_details in parse_package_details(details_dir):
        stats['all'] += 1
        package = Package(package_name, package_details)

        if not package.is_known_package(packages):
            logger.debug('"%s" is not a known package', package_name)
            stats['unknown'] += 1
            continue

        package.search_github_links()
        # FIXME: package.get_repo_info_from_github()
        # TODO: Search repository for gradle files
        # TODO: Parse gradle files for Android ID
        package.set_github_repos(packages)
        # TODO: Canonicalize owner and repo name
        package.match_repos_to_links()
        # TODO: Parse gradle files for android application

        is_unique_repo = package.has_unique_github_repo()

        if not package.has_github_links() and not is_unique_repo:
            logger.debug(
                    '"%s" does not link to Github and has these %d repos '
                    'on Github: %s',
                    package_name,
                    len(package.github_info['repos']),
                    package.github_info['repos'])
            stats['no_github_link'] += 1
        elif not package.has_repo_links() and not is_unique_repo:
            logger.debug(
                    '"%s" does not link to valid repo (%s) and has these %d '
                    'repos on Github: %s',
                    package_name, package.play_info['github_links'],
                    len(package.github_info['repos']),
                    package.github_info['repos'])
            stats['no_repo'] += 1
        elif package.has_too_many_repo_links() and not is_unique_repo:
            # print(package_name)
            # print(json.dumps(package.repos))
            logger.debug(
                    '"%s" has %d repo links', package_name,
                    len(package.repos))
            stats['too_many_repos'] += 1
        else:
            if is_unique_repo:
                stats['unique_repo'] += 1
                repo = package.github_info['repos'][0]
            else:
                repo = package.repos[0]
            stats['valid'] += 1
            yield package_name, repo

    # TODO: Above steps should be performed independently and sequentially.
    #       Move them out into separate generators.
    #       The idea is:
    #        - Gather data and write it to csv file
    #           + get links from google play
    #           + get repositories for packages
    #           + get gradle files
    #              * Application/library definition
    #              * Android ID
    #        - Canonicalize data and write it back to csv file.
    #           + links on google play need to be canonicalized (do they?)
    #        - ...
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    args = parse_cmdline_arguments()
    configure_logger(args.log)
    csv_writer = csv.writer(args.out)
    for row in match_play_and_github(
            args.package_list,
            args.DETAILS_DIRECTORY):
        csv_writer.writerow(row)
