"""Match package names to Github repositories.

TODO

"""

import argparse
import csv
import glob
import json
import logging
import os
import re
import sys
from typing import Any, Union
from typing import Dict, Generator, List, Mapping, Sequence, Set, Tuple
from typing.io import IO
from typing.re import Pattern

Searchable = Union[dict, list, str, int, float, bool, None]
PathSegment = Union[int, str]
Path = Tuple[PathSegment, ...]

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s | [%(levelname)s] %(message)s'
logger = logging.getLogger(__name__)


def parse_cmdline_arguments() -> argparse.Namespace:
    """Define and parse commandline arguments."""
    arguments = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument(
        '-d', '--details-dir',
        type=str,
        help='Directory containing JSON files with details from Google Play.')
    arguments.add_argument(
        '-p', '--package-to-repo',
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
        '--outdir', default='out/', type=str,
        help='Out directory. Default: out/.')
    arguments.add_argument(
        '--log', default=sys.stderr,
        type=argparse.FileType('w'),
        help='Log file. Default: stderr.')
    return arguments.parse_args()


def parse_package_to_repos_file(input_file: IO[str]) -> Dict[str, List[str]]:
    """Parse CSV file mapping package names to repositories.

    :param IO[str] input_file: CSV file to parse.
        The file needs to contain a column `package` and a column
        `all_repos`. `all_repos` contains a comma separated string of
        Github repositories that include an AndroidManifest.xml file for
        package name in column `package`.
    :returns Dict[str, List[str]]: A mapping from package name to
        list of repository names.
    """
    return {
        row['package']: row['all_repos'].split(',')
        for row in csv.DictReader(input_file)
        }


def parse_package_details(details_dir: str) -> Generator[
        Tuple[str, Any], None, None]:
    """Parse all JSON files in details_dir.

    :param str details_dir: Directory to include JSON files from.
    :returns Generator[Tuple[str, Any]]: Generator over tuples of package name
        and parsed JSON.
    """
    for path in glob.iglob('{}/*.json'.format(details_dir)):
        if os.path.isfile(path):
            with open(path, 'r') as details_file:
                filename = os.path.basename(path)
                package_name = os.path.splitext(filename)[0]
                package_details = json.load(details_file)
                yield package_name, package_details


def invert_mapping(packages: Mapping[str, Sequence[str]]) -> Dict[
        str, Set[str]]:
    """Create mapping from repositories to package names.

    :param Mapping[str, Sequence[str]] packages: Mapping of package names to
        a list of repositories.
    :returns Dict[str, Set[str]]: Mapping of repositories to set of package
        names.
    """
    result = {}
    for package, repos in packages.items():
        for repo in repos:
            result.setdefault(repo, set()).add(package)
    return result


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


class RecursiveSearch(object):
    """Recursively search an object parsed from JSON.

    :param Pattern pattern: Compiled regular expression to search for.
    """

    def __init__(self, pattern: Pattern):
        self.pattern = pattern
        self.results = []

    def search(self, haystack: Searchable, path: Path=()):
        """Search haystack for self.pattern.

        Stores matches in self.results. Each match contains a dict containing
        `path` of type `Path` and `match` of type `str`.

        :param Searchable haystack: Parsed JSON to search for self.pattern.
            Accepts all types json.JSONDecoder may return.
        :param Path path: Path of haystack from JSON root.
        """
        if isinstance(haystack, dict):
            self._search_dict(haystack, path)
        elif isinstance(haystack, list):
            self._search_list(haystack, path)
        elif isinstance(haystack, str):
            self._search_str(haystack, path)
        # Ignore numbers, bool and None

    def _search_dict(self, d: Mapping, path: Path):
        for k, v in d.items():
            self.search(v, path + (k,))

    def _search_list(self, l: Sequence, path: Path):
        for index, item in enumerate(l):
            self.search(item, path + (index,))

    def _search_str(self, s: str, path: Path):
        for match in re.findall(self.pattern, s):
            self.results.append({
                'path': path,
                'match': match
                })


class JSONSetEncoder(json.JSONEncoder):
    """Encode sets as lists when dumping JSON."""
    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, set):
            return list(o)
        return json.JSONEncoder.default(self, o)


def match_play_and_github(package_to_repo: IO[str], details_dir: str):
    packages = parse_package_to_repos_file(package_to_repo)
    # repos = invert_mapping(packages)

    # Link from package name on Google Play (key) to Github repo (value)
    play_to_github = []
    # Links from package name on Google Play (value) to Github repo (key)
    github_to_play = {}

    stats = {
            'all': 0,
            'unknown_package': 0,
            'details': {
                'empty': 0,
                'non_empty': 0
                },
            'repo_links': {
                'lt1': 0,
                'eq1': 0,
                'gt1': 0
                },
            'repo_has_manifest': {
                'yes': 0,
                'no': 0
                }
        }

    pattern = re.compile(r'github\.com\/([A-Za-z0-9_-]*\/[A-Za-z0-9_-]*)')
    for package_name, package_details in parse_package_details(details_dir):
        stats['all'] += 1
        if package_name not in packages:
            stats['unknown_package'] += 1
            continue

        #########################
        # TODO
        # Refactor
        #########################

        if package_details:
            stats['details']['non_empty'] += 1
            search = RecursiveSearch(pattern)
            search.search(package_details)
            repo_links = {r['match'] for r in search.results}
            logger.debug(repo_links)

            # TODO: Check if github.com link is actually a repo

            # Only accept link between Google Play and Github as verified if
            # package links to exactly one Github repo.
            if len(repo_links) == 1:
                stats['repo_links']['eq1'] += 1
                repo = repo_links.pop()

                # Github repo must have manifest for package name.
                if repo in packages[package_name]:
                    stats['repo_has_manifest']['yes'] += 1
                    play_to_github.append({
                        'package_name': package_name,
                        'repository': repo
                        })
                    github_to_play.setdefault(repo, []).append(package_name)
                else:
                    stats['repo_has_manifest']['no'] += 1
            elif len(repo_links) < 1:
                stats['repo_links']['lt1'] += 1
            elif len(repo_links) > 1:
                stats['repo_links']['gt1'] += 1
                if stats['repo_links']['gt1'] > 100:
                    pass

        else:
            stats['details']['empty'] += 1

    #    print(json.dumps(play_to_github, indent=1))
    #    print(json.dumps(github_to_play, indent=1))
    stats['duplicate_links'] = sum(
            1 for pn in github_to_play.values() if len(pn) > 1)
    for r, pn in github_to_play.items():
        if len(pn) > 1:
            print(len(pn), " | ", r, ' => ', pn)
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    args = parse_cmdline_arguments()
    configure_logger(args.log)
    match_play_and_github(args.package_to_repo, args.details_dir)


"""
Manually inspected repositories which more than one package from Google Play
link to.

All of them seemingly legitimately host several apps.

This is the list of these repositories:

2  |  timothyleerussell/RationalCalc  =>
    [
    'com.snoffleware.android.rationalcalc',
     'com.snoffleware.android.rationalcalcfree'
    ]
7  |  tnantoka/itoa  =>
    [
    'com.bornneet.dotpict',
     'com.bornneet.editcode',
     'com.bornneet.bubbletodo',
     'com.bornneet.generativepolygon',
     'com.bornneet.capicondemo',
     'com.bornneet.helloworld',
     'com.bornneet.fetchcurrency'
    ]
2  |  isjfk/poweralarm  =>
    [
    'com.isjfk.android.rac',
     'com.isjfk.android.racad'
    ]
3  |  dgoodmaniii/dozenal-droid  =>
    [
    'com.dsadozenal.tgmdroid',
     'com.dsadozenal.dozclockwidget',
     'com.dsadozenal.dozbc'
    ]
2  |  wagoodman/StackAttack  =>
    [
    'com.wagoodman.stackattack.lite',
     'com.wagoodman.stackattack.full'
    ]
2  |  ghisguth/sunlight  =>
    [
    'com.ghisguth.sun',
     'cxa.lineswallpaper'
    ]
6  |  snuk182/aceim  =>
    [
    'aceim.protocol.snuk182.xmpp',
     'aceim.protocol.snuk182.mrim',
     'aceim.protocol.snuk182.icq',
     'aceim.protocol.snuk182.vkontakte',
     'aceim.smileys.flags',
     'aceim.app'
    ]
4  |  hwki/SimpleBitcoinWidget  =>
    [
    'com.brentpanther.litecoinwidget',
     'com.brentpanther.bitcoinwidget',
     'com.brentpanther.ethereumwidget',
     'com.brentpanther.bitcoincashwidget'
    ]
2  |  xdtianyu/CallerInfo  =>
    [
    'org.xdty.callerinfo.plugin',
     'org.xdty.callerinfo'
    ]
2  |  DeviceConnect/DeviceConnect-Android  =>
    [
    'org.deviceconnect.android.deviceplugin.sphero',
     'org.deviceconnect.android.manager'
    ]
2  |  donaldmunro/AARemu  =>
    [
    'to.augmented.reality.android.em.sample',
     'to.augmented.reality.android.em.recorder'
    ]
2  |  jonathangerbaud/Klyph  =>
    [
    'com.abewy.klyph.pro',
     'com.abewy.klyph_beta'
    ]
3  |  reshaping-the-future/better-together  =>
    [
    'ac.robinson.bettertogether.plugin.shopping',
     'ac.robinson.bettertogether.plugin.video',
     'ac.robinson.bettertogether'
    ]
2  |  godstale/retrowatch  =>
    [
    'com.hardcopy.retrowatchle',
     'com.hardcopy.retrowatch'
    ]
2  |  vmihalachi/turbo-editor  =>
    [
    'com.maskyn.fileeditorpro',
     'com.maskyn.fileeditor'
    ]
2  |  groundupworks/flying-photo-booth  =>
    [
    'com.groundupworks.partyphotobooth',
     'com.groundupworks.flyingphotobooth'
    ]
"""
