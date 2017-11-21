# Github Android App Search tool

This script facilitates finding Android apps on Github and matching them with
entries on Google Play.

## Installation

Clone the repository:

```
git clone https://github.com/S2-group/android-app-search
```

Create a virtual environment for `python3`:

```
cd android-app-search/
virtualenv --python=python3 env
```

Activate environment and install requirements:
```
source env/bin/activate
pip install --requirement requirements.txt
```

It is recommended to use an
[authentication token for Github API](https://github.com/blog/1509-personal-api-tokens).
Set it as environment variable `GITHUB_AUTH_TOKEN`:
```
export GITHUB_AUTH_TOKEN="1234abcd...xyz"
```

For step `get_play_data`
[node-google-play-cli](https://github.com/dweinstein/node-google-play-cli)
needs to be installed and configured.


## Usage

Execute `gh_android_apps` to see all sub-commands.
```
./gh_android_apps.py
```

Get more information on each sub-command and its options by appending `-h` or
`--help`. For example:
```
./gh_android_apps.py verify_play_link --help
```

This is the full help output:

```
usage: gh_android_apps.py [-h] [--log LOG] [-v] [-q]
                          {verify_play_link,get_play_data,match_packages,get_repo_data,get_gradle_files,add_gradle_info,clone}
                          ...

Collect data on Android apps on Github.

Combine information from Github and Google Play to find open source Android
apps. Commonly used meta data is parsed into a graph database.

Reads environment variable GITHUB_AUTH_TOKEN to use for authentication with
Github if available. Authenticated requests have higher rate limits.

This script executes several of the interdependent steps as sub-commands. Use
the --help option on a sub-command to learn more about it.

positional arguments:
  {verify_play_link,get_play_data,match_packages,get_repo_data,get_gradle_files,add_gradle_info,clone}
    verify_play_link    Filter out package names not available in Google Play.
                        For each package name in input, check if package name
                        is available in Google Play. If so, print package name
                        to output. Input and output have each package name on
                        a separate lines. Use -h or --help for more
                        information.
    get_play_data       Download package meta data from Google Play. For each
                        package name in input, use node-google-play-cli to
                        fetch meta data from Google Play and store resulting
                        JSON in out directory. Input expects each package name
                        on a separate line. Output JSON files are stored in
                        <outdir>/<package_name>.json. Out directory will be
                        created if it does not exist and individual files will
                        be overwritten if they exist. Executable bulk-details
                        from node-google-play-cli is used to communicate with
                        Google Play (https://github.com/dweinstein/node-
                        google-play-cli).
    get_repo_data       Download information about repositories from Github.
                        Read CSV file as input and write information to output
                        CSV file. Use -h or --help for more information.
    match_packages      Match package names to Github repositories. Use -h or
                        --help for more information.
    get_gradle_files    Download gradle files from repositories on Github.
                        Read CSV file as input and write all files to outdir.
                        Additional output is a CSV file with columns
                        has_gradle_files, renamed_to, and not_found added to
                        content of input file. Use -h or --help for more
                        information.
    add_gradle_info     Add columns to CSV file: 'has_gradle_files',
                        'renamed_to', 'not_found' In an earlier version
                        find_gradle_files.py did not write any information to
                        a CSV file but only stored gradle files it found in a
                        directory for each repository. This script parses the
                        directories for all repositories and extends an input
                        CSV file with above mentioned columns. Use -h or
                        --help for more information.
    clone               Clone Github repositories listed in CSV file. The CSV
                        file needs to contain a column full_name that lists
                        the identifier of the Github repository in the format
                        <ownwer-login>/<repo-name>. Repositories can be
                        filitered by a minimum number of commits requirement.
                        Use -h or --help for more information.

optional arguments:
  -h, --help            show this help message and exit
  --log LOG             Log file. Default: stderr.
  -v, --verbose         Increase log level. May be used several times.
  -q, --quiet           Decrease log level. May be used several times.
```

## Sub-commands

###  Verify Package exists on Google Play

```
usage: gh_android_apps.py verify_play_link [-h] [--input INPUT]
                                           [--output OUTPUT] [--log LOG]
                                           [--include-403]

Filter out package names not available in Google Play.

For each package name in input, check if package name is available in
Google Play. If so, print package name to output.

Input and output have each package name on a separate lines.

Use -h or --help for more information.

optional arguments:
  -h, --help       show this help message and exit
  --input INPUT    File to read package names from. Default: stdin.
  --output OUTPUT  Output file. Default: stdout.
  --log LOG        Log file. Default: stderr.
  --include-403    Include package names which Google Play returns status `403
                   Unauthorized` for.
```

### Download Meta Data for Apps from Google Play


```
usage: gh_android_apps.py get_play_data [-h] [--input INPUT] [--outdir OUTDIR]
                                        [--bulk_details-bin BULK_DETAILS_BIN]

Download package meta data from Google Play.

For each package name in input, use node-google-play-cli to fetch meta
data from Google Play and store resulting JSON in out directory.

Input expects each package name on a separate line.

Output JSON files are stored in <outdir>/<package_name>.json. Out
directory will be created if it does not exist and individual files
will be overwritten if they exist.

Executable bulk-details from node-google-play-cli is used to communicate
with Google Play (https://github.com/dweinstein/node-google-play-cli).

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         File to read package names from. Default: stdin.
  --outdir OUTDIR       Out directory. Default: out/.
  --bulk_details-bin BULK_DETAILS_BIN
                        Path to node-google-play-cli bulk-details binary.
                        Default: /usr/bin/gp-bulk-details
```

### Download Meta Data for Repositories from Github


```
usage: gh_android_apps.py get_repo_data [-h] [-o OUT] [-p PACKAGE_LIST]

Download information about repositories from Github.

Read CSV file as input and write information to output CSV file.

Use -h or --help for more information.

optional arguments:
  -h, --help            show this help message and exit
  -o OUT, --out OUT     CSV file to write meta data to.
  -p PACKAGE_LIST, --package_list PACKAGE_LIST
                        CSV file that matches package names to a repository.
                        The file needs to contain a column for the package
                        name and a second column with the repo name. Default:
                        stdin.
```

### Deduplicate and Match Apps on Google Play and Github

```
usage: gh_android_apps.py match_packages [-h] [-p PACKAGE_LIST] [-o OUT]
                                         DETAILS_DIRECTORY

Match package names to Github repositories.

Use -h or --help for more information.

positional arguments:
  DETAILS_DIRECTORY     Directory containing JSON files with details from
                        Google Play.

optional arguments:
  -h, --help            show this help message and exit
  -p PACKAGE_LIST, --package_list PACKAGE_LIST
                        CSV file that matches package names to repositories.
                        The file needs to contain a column `package` and a
                        column `all_repos`. `all_repos` contains a comma
                        separated string of Github repositories that include
                        an AndroidManifest.xml file for package name in column
                        `package`. Default: stdin.
  -o OUT, --out OUT     File to write CSV output to. Default: stdout
```

### Download Gradle Files from Repositories

```
usage: gh_android_apps.py get_gradle_files [-h] [--outdir OUTDIR]
                                           [-r REPO_LIST]
                                           [--output_list OUTPUT_LIST]

Download gradle files from repositories on Github.
Read CSV file as input and write all files to outdir. Additional output is a
CSV file with columns has_gradle_files, renamed_to, and not_found added to
content of input file.

Use -h or --help for more information.

optional arguments:
  -h, --help            show this help message and exit
  --outdir OUTDIR       Directory to safe gradle files to. Default:
                        out/gradle_files.
  -r REPO_LIST, --repo_list REPO_LIST
                        CSV file that contains repository names. The file
                        needs to contain a column 'full_name'. Default: stdin.
  --output_list OUTPUT_LIST
                        CSV file to write updated repository information to.
                        This file will contain the same information as
                        REPO_LIST extended with three columns:
                        has_gradle_files, renamed_to, and not_found. These
                        columns indicate if the repository contains at least
                        one gradle configuration file, the name the repository
                        has been renamed to, and if the repository has not
                        been found anymore, respectively.
```

### Parse Gradle File Availability

```
usage: gh_android_apps.py add_gradle_info [-h] [--outdir OUTDIR]
                                          [-r REPO_LIST]
                                          [--output_list OUTPUT_LIST]

Add columns to CSV file: 'has_gradle_files', 'renamed_to', 'not_found'

In an earlier version find_gradle_files.py did not write any information to a
CSV file but only stored gradle files it found in a directory for each
repository.

This script parses the directories for all repositories and extends an input
CSV file with above mentioned columns.

Use -h or --help for more information.

optional arguments:
  -h, --help            show this help message and exit
  --outdir OUTDIR       Directory to read gradle files from. Default:
                        out/gradle_files.
  -r REPO_LIST, --repo_list REPO_LIST
                        CSV file that contains repository names. The file
                        needs to contain a column 'full_name'. Default: stdin.
  --output_list OUTPUT_LIST
                        CSV file to write updated repository information to.
                        This file will contain the same information as
                        REPO_LIST extended with three columns:
                        has_gradle_files, renamed_to, and not_found. These
                        columns indicate if the repository contains at least
                        one gradle configuration file, the name the repository
                        has been renamed to, and if the repository has not
                        been found anymore, respectively.
```

### Clone Repositories from Github

```
usage: gh_android_apps.py clone [-h] [-o OUTDIR] [-r REPO_LIST]
                                [-c MIN_COMMITS]

Clone Github repositories listed in CSV file.

The CSV file needs to contain a column full_name that lists the identifier of
the Github repository in the format <ownwer-login>/<repo-name>.

Repositories can be filitered by a minimum number of commits requirement.

Use -h or --help for more information.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTDIR, --outdir OUTDIR
                        Prefix to clone repositories into. Default:
                        out/github_repos.
  -r REPO_LIST, --repo_list REPO_LIST
                        CSV file that contains repository names. The file
                        needs to contain a column 'full_name'. Default: stdin.
  -c MIN_COMMITS, --min_commits MIN_COMMITS
                        Minimum number of commits in main branch for
                        repository to be cloned. CSV file needs to have column
                        commit_count for this to work.
```
