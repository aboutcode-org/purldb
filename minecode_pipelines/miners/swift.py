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


def is_safe_repo_url(repo_url: str) -> bool:
    parsed = urlparse(repo_url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and parsed.path.endswith(".git")
        or parsed.path.count("/") >= 2
    )


def fetch_tags_raw(repo_url: str, timeout: int = 60, logger=None) -> str | None:
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
