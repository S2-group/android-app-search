"""Download gradle files from repositories on Github.

Read CSV file as input and write all files to outdir.
"""
import argparse
import csv
import logging
import os
import sys
from typing import Iterator
from github3.repos.contents import Contents
from github3.search import CodeSearchResult
from util import log
from util.ratelimited_github import RateLimitedGitHub


__log__ = logging.getLogger(__name__)


class GradleFileSearcher(RateLimitedGitHub):
    """Wrapper for Github API to download gradle files."""

    def search_gradle_files(self, repo: str) -> Iterator[CodeSearchResult]:
        """Search for gradle files in repository.

        This search term includes all files with either of build.gradle or
        settings.gradle anywhere in the path. Thus also unrelated files as
        foo/bar/settings.gradle/example.txt

        :param str repo:
            Full name of repository.
        :returns Iterator[CodeSearchResult]:
            Iterator over search results.
        """
        return self.search_code(
            'repo:{} in:path build.gradle OR settings.gradle'.format(repo))

    def iter_gradle_files(self, repo_name: str) -> Iterator[Contents]:
        """Iterate over gradle files in repostitory.

        :param str full_name:
            Identifier of Github repository in format <repo-owner>/<repo-name>.
        :returns Iterator[Contents]:
            Iterator over gradle files in repository.
        """
        for result in self.search_gradle_files(repo_name):
            # Filter out files that are not gradle files but have gradle in
            # their prefix
            if result.path.endswith('.gradle'):
                yield result.repository.contents(result.path)


def makedirs(path: str):
    """Recursively create directories.

    :param str path:
        Full path including filename. Basename will be stripped unless it
        ends in /.
    """
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)


def download_gradle_files(
        repo_name: str, github: GradleFileSearcher, outdir: str):
    """Download gradle files from repository.

    All files will end up in subdirectories of the following template:
    <outdir>/<repo_name>/<path_in_repo>/build.gradle

    :param str repo_name:
        Identifier of Github repository in format <repo-owner>/<repo-name>.
    :param GradleFileSearcher github:
        Github API wrapper to download gradle files.
    :param str outdir:
        Name of directory to download files to.
    """
    for gradle_file in github.iter_gradle_files(repo_name):
        path = os.path.join(outdir, repo_name, gradle_file.path)
        makedirs(path)
        with open(path, 'wb') as output_file:
            # Ensure input to write() is of type bytes even if emtpy
            output_file.write(gradle_file.decoded or b'')


def parse_cmdline_arguments() -> argparse.Namespace:
    """Define and parse commandline arguments."""
    arguments = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument(
        '-o', '--outdir', default='out/gradle_files', type=str,
        help='Directory to safe gradle files to. Default: out/gradle_files.')
    arguments.add_argument(
        '-r', '--repo_list',
        default=sys.stdin,
        type=argparse.FileType('r'),
        help='''CSV file that contains repository names. The file needs
            to contain a column 'full_name'. Default: stdin.''')
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
    github = GradleFileSearcher(token=token)
    csv_reader = csv.DictReader(args.repo_list)
    for row in csv_reader:
        repo_name = row['full_name']
        if repo_name:
            __log__.info('Get gradle files in %s', repo_name)
            download_gradle_files(repo_name, github, args.outdir)
        else:
            __log__.warning(
                'Package %s does not contain a repo name.', row['full_name'])


if __name__ == '__main__':
    ARGS = parse_cmdline_arguments()
    log.configure_logger(__package__, ARGS.log, ARGS.verbose, ARGS.quiet)
    TOKEN = os.getenv('GITHUB_AUTH_TOKEN')
    main(ARGS, TOKEN)
