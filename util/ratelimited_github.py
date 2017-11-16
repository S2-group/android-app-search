"""GitHub API wrapper that adheres to rate limit.

Access to Github API v3 is rate limited. Many of the API GET requests from
this wrapper automatically wait for reset if rate limit is reached. This
is achieved by overriding _get and _iter methods.

Rate limit data is read from headers of last response if available. If
there is not response available, rate limit information is requested from
the /rate_limit endpoint of the Github API v3. For more information see
https://developer.github.com/v3/rate_limit/
"""

import sys

from datetime import datetime
from github3 import GitHub
from github3.models import GitHubCore
from github3.repos.repo import Repository
from github3.structs import GitHubIterator
import time


# FIXME: Use logging instead of makeshift class
class TestLogger(object):
    def log(self, *args, **kwargs):
        print(*args, **kwargs, file=sys.stderr)

    def debug(self, *args, **kwargs):
        self.log('[DEBUG] ', *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log('[INFO] ', *args, **kwargs)

    def warn(self, *args, **kwargs):
        self.log('[WARN] ', *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log('[ERROR] ', *args, **kwargs)

    def exception(self, *args, **kwargs):
        self.log('[EXCEPTION] ', *args, **kwargs)

    def critical(self, *args, **kwargs):
        self.log('[CRITICAL] ', *args, **kwargs)


__logger__ = TestLogger()


class RateLimitedGitHub(GitHubCore):
    """Provides functionality to wait avoid rate limit."""
    RATELIMIT_LIMIT_HEADER = 'X-RateLimit-Limit'
    RATELIMIT_REMAINING_HEADER = 'X-RateLimit-Remaining'
    RATELIMIT_RESET_HEADER = 'X-RateLimit-Reset'

    CORE_RESOURCE = 'core'
    SEARCH_RESOURCE = 'search'
    GRAPHQL_RESOURCE = 'graphql'

    def _get_ratelimit(self, resource: str=CORE_RESOURCE) -> dict:
        """Fetch rate limit information from API.

        :param str resource:
            Name of resource to get rate limit for. Either CORE_RESOURCE,
            SEARCH_RESOURCE, or GRAPHQL_RESOURCE.
        :returns dict:
            Dictionary containing remaining rate limit, full rate limit, and
            reset time as POSIX timestamp.  For more information see
            https://developer.github.com/v3/rate_limit/
        """
        uri = self._github_url + '/rate_limit'
        json = self._json(self._session.get(uri), 200)
        return json.get('resources', {}).get(resource, {})

    def _response_has_ratelimit_headers(self) -> bool:
        """Tests if rate limit headers are present in response.

        :returns bool:
            True if all necessary headers are present, False otherwise.
        """
        response = self.last_response
        return (response and response.headers and
                self.RATELIMIT_RESET_HEADER in response.headers and
                self.RATELIMIT_LIMIT_HEADER in response.headers and
                self.RATELIMIT_REMAINING_HEADER in response.headers)

    def _get_ratelimit_from_headers(self) -> dict:
        """Read rate limit information from response headers.

        :returns dict:
            Dictionary containing remaining rate limit, full rate limit, and
            reset time as POSIX timestamp.  For more information see
            https://developer.github.com/v3/rate_limit/
        """
        headers = self.last_response.headers
        return {
                'limit': headers.get(self.RATELIMIT_LIMIT_HEADER),
                'remaining': headers.get(self.RATELIMIT_REMAINING_HEADER),
                'reset': headers.get(self.RATELIMIT_RESET_HEADER)
                }

    def _has_response(self) -> bool:
        """Test if this class has a last_response member."""
        return hasattr(self, 'last_response') and getattr(
                self, 'last_response')

    def _wait_for_ratelimit(self, resource: str=CORE_RESOURCE):
        """Waits until ratelimit refresh if necessary.

        Rate limit is read from headers of last response if this class has
        a `last_response` member.

        :param str resource:
            Name of resource to get rate limit for. Either CORE_RESOURCE,
            SEARCH_RESOURCE, or GRAPHQL_RESOURCE.
        """
        if self._has_response() and self._response_has_ratelimit_headers():
            ratelimit = self._get_ratelimit_from_headers()
        else:
            ratelimit = self._get_ratelimit()
        if int(ratelimit.get('remaining', '0')) < 1:
            reset = int(ratelimit.get('reset', '0'))
            now = int(datetime.utcnow().timestamp())
            wait_time = reset - now + 1
            if wait_time > 0:
                time.sleep(wait_time)

    def _get(self, url, **kwargs):
        """Rate limited version of _get."""
        self._wait_for_ratelimit()
        return self._session.get(url, **kwargs)

    def _iter(self, count, url, cls, params=None, etag=None):
        """Rate limited iterator for this project.

        :param int count: How many items to return.
        :param int url: First URL to start with
        :param class cls: cls to return an object of
        :param params dict: (optional) Parameters for the request
        :param str etag: (optional), ETag from the last call
        """
        return RateLimitedIterator(count, url, cls, self, params, etag)


class RateLimitedIterator(RateLimitedGitHub, GitHubIterator):
    """Rate limited version of GitHubIterator."""
    pass


class RateLimitedRepository(RateLimitedGitHub, Repository):
    """Rate limited version of Repository."""
    pass


class RateLimitedGitHub(RateLimitedGitHub, GitHub):
    """Rate limited version of GitHub."""

    def repository(self, owner, repository):
        """Returns a Repository object for the specified combination of
        owner and repository

        :param str owner: (required)
        :param str repository: (required)
        :returns: :class:`Repository <github3.repos.Repository>`
        """
        repo = super(RateLimitedGitHub, self).repository(owner, repository)
        return RateLimitedRepository(repo.to_json(), self) if repo else None


# TODO: Rate limited versions of
#        - methods: create_gist, create_issue, create_repo, gist, issue,...
#        - classes: Gist, Issue, Search, Organization, ...
#        - ...
