#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import brotli
import json
import requests
import time

from packageurl import PackageURL


NIX_TYPE = "nix"
NIXPKGS = "nixpkgs"
DELAY_MULTIPLIER = 2
MAX_RETRIES = 3


def get_all_nix_packages(channel_url, logger=None):
    """Get all Nix packages"""
    if logger:
        logger(f"Fetching Nix packages from: {channel_url}")
    response = requests.get(channel_url)
    response.raise_for_status()

    try:
        decompressed_data = brotli.decompress(response.content)
        data = json.loads(decompressed_data)
    except brotli.error:
        data = response.json()

    packages_dict = data.get("packages", {})
    return packages_dict


def get_all_nix_packages_name(packages_dict, logger=None):
    """Get all Nix packages name"""
    all_package_names = []
    packages = list(packages_dict.keys())
    for attr_path in packages:
        all_package_names.append(attr_path)

    return {"packages": all_package_names}


def load_nix_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    return packages_data.get("packages", [])


def get_nix_packageurls(name, packages_dict, logger=None):
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
            break
        except requests.HTTPError as e:
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = DELAY_MULTIPLIER**attempt
                if logger:
                    logger(f"Rate limited (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                # The package_dict contains the package's current version
                # devbox.sh may have only index the top
                # level, all others deeper level may not be indexed
                # TODO: This can only get the current version.
                version = get_version_from_package_dict(name, packages_dict)
                if version:
                    purl = PackageURL(type=NIX_TYPE, namespace=NIXPKGS, name=name, version=version)
                else:
                    purl = PackageURL(type=NIX_TYPE, namespace=NIXPKGS, name=name)
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
            purl = PackageURL(type=NIX_TYPE, namespace=NIXPKGS, name=name, version=version)
            purl_string = purl.to_string()
            if purl_string not in packageurls:
                packageurls.append(purl_string)

    return packageurls


def get_version_from_package_dict(name, package_dict):
    """Get the version data from the package_dict"""
    package_info = package_dict.get(name)
    if not package_info:
        return None
    return package_info.get("version")


def yield_nix_package_data(name, packageurls=[]):
    for purl in packageurls:
        package_url = PackageURL.from_string(purl)
        package_data_url = (
            f"https://search.devbox.sh/v2/resolve?name={name}&version={package_url.version}"
        )
        response = requests.get(package_data_url)
        if not response.ok:
            continue
        yield purl, response.json()
