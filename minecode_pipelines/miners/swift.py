#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import shutil
import subprocess
from urllib.parse import urlparse

"""
Clone the Swift Index repo (https://github.com/SwiftPackageIndex/PackageList) and the Minecode Pipelines Swift repo.
Read the packages.json file from the Swift Index repo to get a list of Git repositories.
Fetch the tags for each repo using the git ls-remote command,
then create package URLs for each repo with its version and store them in the Minecode Pipelines Swift repo.
"""


def is_safe_repo_url(repo_url: str) -> bool:
    """Return True if the URL is HTTPS GitHub with .git suffix or has at least two path segments."""
    parsed = urlparse(repo_url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and parsed.path.endswith(".git")
        or parsed.path.count("/") >= 2
    )


def fetch_git_tags_raw(repo_url: str, timeout: int = 60, logger=None) -> str | None:
    """Run `git ls-remote` on a GitHub repo and return raw output, or None on error."""
    git_executable = shutil.which("git")
    if git_executable is None:
        logger("Git executable not found in PATH")
        return None

    if not is_safe_repo_url(repo_url):
        raise ValueError(f"Unsafe repo URL: {repo_url}")

    try:
        result = subprocess.run(
            [git_executable, "ls-remote", repo_url],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger(f"Failed to fetch tags for {repo_url}: {e}")
    except subprocess.TimeoutExpired:
        logger(f"Timeout fetching tags for {repo_url}")
    return None


# FIXME duplicated with miners github
def split_org_repo(url_like):
    """
    Given a URL-like string to a GitHub repo or a repo name as in org/name,
    split and return the org and name.

    For example:
    >>> split_org_repo('foo/bar')
    ('foo', 'bar')
    >>> split_org_repo('https://api.github.com/repos/foo/bar/')
    ('foo', 'bar')
    >>> split_org_repo('github.com/foo/bar/')
    ('foo', 'bar')
    >>> split_org_repo('git://github.com/foo/bar.git')
    ('foo', 'bar')
    """
    segments = [s.strip() for s in url_like.split("/") if s.strip()]
    if not len(segments) >= 2:
        raise ValueError(f"Not a GitHub-like URL: {url_like}")
    org = segments[-2]
    name = segments[-1]
    if name.endswith(".git"):
        name, _, _ = name.rpartition(".git")
    return org, name
