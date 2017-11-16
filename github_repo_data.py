"""Download information about repositories from Github.

Read CSV file as input and write information to output CSV file.
"""
import argparse
import csv
import logging
import os
import sys
from util import log
from util.github_repo import RepoVerifier


__log__ = logging.getLogger(__name__)


CSV_COLUMNS = [
    'id', 'name', 'full_name', 'description', 'size', 'private', 'fork',
    'archived', 'created_at', 'updated_at', 'pushed_at', 'language',
    'default_branch', 'homepage', 'forks_count', 'stargazers_count',
    'subscribers_count', 'watchers_count', 'network_count', 'has_downloads',
    'has_issues', 'has_pages', 'has_projects', 'has_wiki', 'owner_id',
    'owner_login', 'owner_type', 'parent_id', 'source_id', 'commit_count'
    ]


def download_repo_data(full_name: str, github: RepoVerifier) -> dict:
    """Download data about repository.

    :param str full_name:
        Identifier of Github repository in format <repo-owner>/<repo-name>.
    :param RepoVerifier github:
        Github API wrapper to access Github data.
    :returns dict:
        Mapping of meta data names to values.
    """
    repo = github.get_repo(full_name)
    if repo:
        data = repo.meta_data
        data['commit_count'] = repo.count_commits()
        return data
    __log__.warning('Cannot get repository %s', full_name)
    return None


def parse_cmdline_arguments() -> argparse.Namespace:
    """Define and parse commandline arguments."""
    arguments = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument(
        '-o', '--out', default=sys.stdout,
        type=argparse.FileType('w'),
        help='CSV file to write meta data to.')
    arguments.add_argument(
        '-p', '--package_list',
        default=sys.stdin,
        type=argparse.FileType('r'),
        help='''CSV file that matches package names to a repository.
            The file needs to contain a column for the package name and
            a second column with the repo name. Default: stdin.''')
    arguments.add_argument(
        '--log', default=sys.stderr,
        type=argparse.FileType('w'),
        help='Log file. Default: stderr.')
    arguments.add_argument(
        '-v', '--verbose', default=0, action='count',
        help='Increase log level. May be used several times.')
    arguments.add_argument(
        '-q', '--quiet', default=0, action='count',
        help='Decrease log level. May be used several times.')
    return arguments.parse_args()


def main(args: argparse.Namespace, token: str):
    """Download info for repos in input to CSV file.

    :param argparse.Namespace args:
        Command line arguments.
    :param str token:
        Token to use for authentication with Github.
    """
    repo_verifier = RepoVerifier(token=token)
    csv_reader = csv.reader(args.package_list)
    csv_writer = csv.DictWriter(args.out, CSV_COLUMNS)
    csv_writer.writeheader()
    for row in csv_reader:
        if len(row) > 1:
            repo_name = row[1]
            __log__.info('Get data for %s', repo_name)
            data = download_repo_data(repo_name, repo_verifier)
            if data:
                csv_writer.writerow(data)
        else:
            __log__.warning(
                'Package %s does not contain a repo name.', row[0])


if __name__ == '__main__':
    ARGS = parse_cmdline_arguments()
    log.configure_logger(__package__, ARGS.log, ARGS.verbose, ARGS.quiet)
    TOKEN = os.getenv('GITHUB_AUTH_TOKEN')
    main(ARGS, TOKEN)
