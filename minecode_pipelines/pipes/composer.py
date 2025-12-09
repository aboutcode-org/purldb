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
from minecode_pipelines.utils import get_temp_file
from aboutcode.hashid import get_core_purl
import requests
from packageurl import PackageURL
from minecode_pipelines.utils import cycle_from_index, grouper

PACKAGE_BATCH_SIZE = 100


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
        return None, purls

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

    base_purl = None
    if purls:
        first_purl = purls[0]
        base_purl = get_core_purl(first_purl)
    return base_purl, purls


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


def mine_composer_packages():
    """Mine Composer package names from Packagist and return List of (vendor, package) tuples."""
    packages_file = get_composer_packages()
    return load_composer_packages(packages_file)


def mine_composer_packageurls(packages, start_index):
    """Mine Composer packages from Packagist"""
    packages_iter = cycle_from_index(packages, start_index)
    for batch_index, package_batch in enumerate(
        grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_iter)
    ):
        for item in package_batch:
            if not item:
                continue

            vendor, package = item
            yield get_composer_purl(vendor=vendor, package=package)
