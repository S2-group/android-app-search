"""Match package names to Github repositories.

TODO
"""

import argparse
import csv
import json
import logging
import sys
from typing import Any, List, Mapping, Set
from typing.io import IO

from util.parse import ParsedJSON
from util.parse import parse_package_details, parse_package_to_repos_file
from util.recursive_search import GithubLinkSearch


LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s | [%(levelname)s] %(message)s'
logger = logging.getLogger(__name__)


class Package(object):
    """Representation of an Android package.

    A Package is used to match a package in open source Github repositories to
    a package on Google Play.

    :param str package_name: Package name as defined in Android manifest file
        and used as identifier on Google Play.
    :param ParsedJSON google_play_details: Details from Google Play parsed from
        JSON.
    """
    def __init__(self, package_name: str, google_play_details: ParsedJSON):
        self.package_name = package_name
        self.play_info = {'details': google_play_details}
        self.github_info = {}
        self.repos = []

    def is_known_package(self, known_packages: Mapping[str, Any]) -> bool:
        """Test if name of this package is in packages.

        :param Mapping[str, Any] known_packages: Dict with package names as
            keys.
        :returns bool: True if self.package_name is a key in known_packages,
            False otherwise.
        """
        return self.package_name in known_packages

    def search_github_links(self) -> Set[str]:
        """Search package details for Github links.

        Links to Github are stored with their two initial path segments that
        potentially equal to a repository identifier.

        Examples:
            https://github.com/blog/category/engineering
            --> blog/category

            https://github.com/google/battery-historian/blob/master/README.md
            --> google/battery-historian

        :returns Set[str]: Set of first two path segments of links to Github
            found in Google Play Details for this package.
        """
        search = GithubLinkSearch()
        search.search(self.play_info['details'])
        self.play_info.update({
                'search_results': search.results,
                'github_links': {r['match'] for r in search.results}
                })
        return self.play_info['github_links']

    def set_github_repos(self, known_packages: Mapping[str, List[str]]):
        """Set repositories stored for this package name in packages.

        :param Dict[str, List[str]] known_packages: A mapping from package name
            to list of Github repositories that contain a manifest file for the
            key.
        """
        self.github_info['repos'] = known_packages.get(self.package_name, [])

    def has_unique_github_repo(self) -> bool:
        """Test if only one repository on GitHub mentions this package."""
        return len(set(self.github_info['repos'])) == 1

    def has_github_links(self) -> bool:
        """Test if Google Play details contain at least one link to Github."""
        return len(self.play_info['github_links']) > 0

    def has_repo_links(self) -> bool:
        """Test if Google Play details contain at least one link to a matching
        repo.
        """
        return len(self.repos) > 0

    def has_too_many_repo_links(self) -> bool:
        """Test if Google Play details contain more than one repo link."""
        return len(self.repos) > 1

    def _link_is_valid_repo(self, link: str) -> bool:
        """Test if potential repository link is valid.

        :returns bool: True if repository described by link contains an
            Android manifest file for this package.
        """
        return link in self.github_info['repos']

    def match_repos_to_links(self):
        """Find repositories with link from Google Play that also contain a
        manifest for the same package name.
        """
        self.repos += list(filter(
                self._link_is_valid_repo,
                self.play_info['github_links']))


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
