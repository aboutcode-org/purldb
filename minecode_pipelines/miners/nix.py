#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import json
import subprocess
from pathlib import Path
import requests
import time

from packageurl import PackageURL


NIX_TYPE = "nix"
DELAY_MULTIPLIER = 2
MAX_RETRIES = 3


def get_nix_packages(nixpkgs_repo, logger=None):
    """Get ALL Nix package names from the nixpkgs repository"""
    all_package_names = []

    repo_path = Path(nixpkgs_repo.working_dir).resolve()

    # Use the `nix-env -qaP` to collect all the packages
    result = subprocess.run(
        ["nix-env", "-qaP", "-f", str(repo_path)],
        capture_output=True,
        text=True
    )
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            name = line.split()
            if name:
                all_package_names.append(name[0])
    if logger:
        logger(f"Total packages found in nixpkgs: {len(all_package_names)}")
    return {"packages": all_package_names}


def load_nix_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    return packages_data.get("packages", [])


def get_nix_packageurls(name, repo_path, logger=None):
    packageurls = []
    data = []
    # Get all the version of a package from the following API:
    # https://search.devbox.sh/v2/pkg?name={name}
    url = f"https://search.devbox.sh/v2/pkg?name={name}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            break  # success, exit retry loop
        except requests.HTTPError as e:
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = DELAY_MULTIPLIER ** attempt
                if logger:
                    logger(f"Rate limited (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                # Use `nix --experimental-features "nix-command" eval` to
                # get the version
                # devbox.sh may have only index the top
                # level, all others deeper level may not be indexed, so we
                # need to use the `nix` to get the package's version
                # TODO: This can only get the current version.
                version = get_version_from_nix(name, repo_path)
                if version:
                    purl = PackageURL(type=NIX_TYPE, name=name, version=version)
                    packageurls.append(purl.to_string())
                return packageurls
            else:
                if logger:
                    logger(f"Request failed: {e}")
                    logger(f"HTTP error {response.status_code}: {response.text}")
                return packageurls
        except requests.RequestException as e:
            if logger:
                logger(f"Request failed: {e}")
            return packageurls
        except ValueError as e:
            if logger:
                logger(f"JSON parsing failed: {e}")
            return packageurls
    if not data:
        # No data collected after retries
        if logger:
            logger(f"Max retries reached. Skipping package: {name}")
        return packageurls

    releases = data.get("releases", [])
    for release in releases:
        version = release.get("version")
        if version:
            purl = PackageURL(type=NIX_TYPE, name=name, version=version)
            purl_string = purl.to_string()
            if purl_string not in packageurls:
                packageurls.append(purl_string)

    return packageurls


def get_version_from_nix(name, repo_path):
    pattern = f"{name}.version"
    result = subprocess.run(
        ["nix", "--experimental-features", "nix-command", "eval", "-f", str(repo_path), pattern, "--json"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        info = json.loads(result.stdout)
        # info should be just a string
        version = info.strip('"') if isinstance(info, str) else info
        return version

    return None


def yield_nix_package_data(name, packageurls=[]):
    for purl in packageurls:
        package_url = PackageURL.from_string(purl)
        package_data_url = f"https://search.devbox.sh/v2/resolve?name={name}&version={package_url.version}"
        response = requests.get(package_data_url)
        if not response.ok:
            continue
        yield purl, response.json()
