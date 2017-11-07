"""Parse intermediary files for further processing."""

import csv
import glob
import json
import os
from typing import Union
from typing import Dict, Generator, List, Mapping, Sequence, Set, Text, Tuple
from typing.io import IO


ParsedJSON = Union[
        Mapping[Text, 'ParsedJSON'], Sequence['ParsedJSON'], Text, int, float,
        bool, None]


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
        Tuple[str, ParsedJSON], None, None]:
    """Parse all JSON files in details_dir.

    Filenames need to have .json extension. Filename without extension is
    assumed to be package name for details contained in file.

    :param str details_dir: Directory to include JSON files from.
    :returns Generator[Tuple[str, ParsedJSON]]: Generator over tuples of
        package name and parsed JSON.
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
