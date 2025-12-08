# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import json
from pathlib import Path
from packageurl import PackageURL

from minecode_pipelines.utils import cycle_from_index, grouper
import shutil
import subprocess
from urllib.parse import urlparse

PACKAGE_BATCH_SIZE = 100


def mine_swift_packageurls(packages_urls, start_index, logger):
    """Mine Swift PackageURLs from package index."""

    packages_iter = cycle_from_index(packages_urls, start_index)
    for batch_index, package_batch in enumerate(
        grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_iter)
    ):
        for package_repo_url in package_batch:
            if not package_repo_url:
                continue
            logger(f"Processing package repo URL: {package_repo_url}")
            git_ls_remote = fetch_git_tags_raw(package_repo_url, 60, logger)
            if not git_ls_remote:
                continue

            tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)
            if not tags_and_commits:
                continue

            yield generate_package_urls(
                package_repo_url=package_repo_url, tags_and_commits=tags_and_commits, logger=logger
            )


def load_swift_package_urls(swift_index_repo):
    packages_path = Path(swift_index_repo.working_dir) / "packages.json"
    with open(packages_path) as f:
        packages_urls = json.load(f)
    return packages_urls


def generate_package_urls(package_repo_url, tags_and_commits, logger):
    org, name = split_org_repo(package_repo_url, logger)
    if not org or not name:
        return None, []
    org = "github.com/" + org
    base_purl = PackageURL(type="swift", namespace=org, name=name)
    updated_purls = []

    for tag, commit in tags_and_commits:
        purl = None
        if tag == "HEAD":
            if len(tags_and_commits) == 1:
                purl = PackageURL(
                    type="swift", namespace=org, name=name, version=commit
                ).to_string()
        else:
            purl = PackageURL(type="swift", namespace=org, name=name, version=tag).to_string()

        if purl:
            updated_purls.append(purl)
    logger(f"Generated {len(updated_purls)} and base PURL: {base_purl} PackageURLs for {package_repo_url}")
    return base_purl, updated_purls


def is_safe_repo_url(repo_url: str) -> bool:
    """Return True if the URL is HTTPS GitHub with .git suffix or has at least two path segments."""
    parsed = urlparse(repo_url)
    return (
        parsed.scheme == "https" and parsed.netloc == "github.com" and parsed.path.endswith(".git")
    )


def fetch_git_tags_raw(repo_url: str, timeout: int = 60, logger=None) -> str | None:
    """Run `git ls-remote` on a GitHub repo and return raw output, or None on error."""
    git_executable = shutil.which("git")
    if git_executable is None:
        logger("Git executable not found in PATH")
        return None
    
    if not repo_url:
        logger("No repository URL provided")
        return None

    if not is_safe_repo_url(repo_url):
        logger(f"Unsafe repository URL: {repo_url}")
        return None

    try:
        result = subprocess.run(  # NOQA
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
def split_org_repo(url_like, logger):
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
        logger(f"Could not parse org and name from URL-like: {url_like}")
        return None, None
    org = segments[-2]
    name = segments[-1]
    if name.endswith(".git"):
        name, _, _ = name.rpartition(".git")
    return org, name


def get_tags_and_commits_from_git_output(git_ls_remote):
    """
    Yield tuples of (tag, commit), given a git ls-remote output
    """
    tags_and_commits = []
    for line in git_ls_remote.split("\n"):
        # line: kjwfgeklngelkfjofjeo123   refs/tags/1.2.3
        line_segments = line.split("\t")
        # segments: ["kjwfgeklngelkfjofjeo123", "refs/tags/1.2.3"]
        if len(line_segments) > 1 and (
            line_segments[1].startswith("refs/tags/") or line_segments[1] == "HEAD"
        ):
            commit = line_segments[0]
            tag = line_segments[1].replace("refs/tags/", "")
            tags_and_commits.append((tag, commit))
    return tags_and_commits
