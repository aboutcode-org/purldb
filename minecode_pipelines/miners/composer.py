#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
from minecode_pipelines.utils import get_temp_file
import requests
from packageurl import PackageURL


def get_composer_packages():
    """
    Fetch all Composer packages from Packagist and save them to a temporary JSON file.
    Response example:
    {
        "packageNames" ["0.0.0/composer-include-files", "0.0.0/laravel-env-shim"]
    }
    """

    response = requests.get("https://packagist.org/packages/list.json")
    if not response.ok:
        return

    packages = response.json()
    temp_file = get_temp_file("ComposerPackages", "json")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(packages, f, indent=4)

    return temp_file


def get_composer_purl(vendor, package):
    """
    Fetch all available Package URLs (purls) for a Composer package from Packagist.
    Response example:
    {
      "minified": "composer/2.0",
      "packages": [
        {
          "monolog/monolog": {
            "0": {
              "name": "monolog/monolog",
              "version": "3.9.0"
            }
          }
        }
      ],
      "security-advisories": [
        {
          "advisoryId": "PKSA-dmw8-jd8k-q3c6",
          "affectedVersions": ">=1.8.0,<1.12.0"
        }
      ]
    }
    get_composer_purl("monolog", "monolog")
    -> ["pkg:composer/monolog/monolog@3.9.0", "pkg:composer/monolog/monolog@3.8.0", ...]
    """
    purls = []
    url = f"https://repo.packagist.org/p2/{vendor}/{package}.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return purls

    data = response.json()
    packages = data.get("packages", {})
    releases = packages.get(f"{vendor}/{package}", [])

    for release in releases:
        version = release.get("version")
        if version:
            purl = PackageURL(
                type="composer",
                namespace=vendor,
                name=package,
                version=version,
            )
            purls.append(purl.to_string())

    return purls


def load_composer_packages(packages_file):
    """Load and return a list of (vendor, package) tuples from a JSON file."""
    with open(packages_file, encoding="utf-8") as f:
        packages_data = json.load(f)

    package_names = packages_data.get("packageNames", [])
    result = []

    for item in package_names:
        if "/" in item:
            vendor, package = item.split("/", 1)
            result.append((vendor, package))

    return result
