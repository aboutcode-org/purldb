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
# under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an “AS IS” BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.


import json
import re

from packageurl import PackageURL

from aboutcode.pipeline import LoopProgress


NUGET_PURL_METADATA_REPO = "https://github.com/aboutcode-data/minecode-data-nuget-test"


def get_catalog_page_count(catalog_index):
    if catalog_index.exists():
        with catalog_index.open("r", encoding="utf-8") as f:
            index = json.load(f)
            return index.get("count", 0)
    return 0


def collect_package_versions(events, package_versions, skipped_packages):
    """Collect package versions from events in the NuGet package catalog."""
    for event in events or []:
        if event["@type"] != "nuget:PackageDetails":
            continue
        pkg_name = event["nuget:id"]

        # Skip package names that resemble NuGet API key and can't be pushed to GitHub.
        if bool(re.fullmatch(r"oy2[a-z0-9]{43}", pkg_name)):
            skipped_packages.add(pkg_name)
            continue

        purl = PackageURL(type="nuget", name=pkg_name).to_string()
        if purl not in package_versions:
            package_versions[purl] = set()

        package_versions[purl].add(event["nuget:version"])


def mine_nuget_package_versions(catalog_path, logger):
    """Mine NuGet package and versions from NuGet catalog."""
    catalog = catalog_path / "catalog"
    catalog_count = get_catalog_page_count(catalog / "index.json")
    catalog_pages = catalog / "pages"

    package_versions = {}
    skipped_packages = set()
    logger(f"Collecting versions from {catalog_count:,d} NuGet catalog.")
    progress = LoopProgress(total_iterations=catalog_count, logger=logger)
    for page in progress.iter(catalog_pages.rglob("*.json")):
        with page.open("r", encoding="utf-8") as f:
            page_catalog = json.load(f)

        collect_package_versions(
            events=page_catalog["items"],
            package_versions=package_versions,
            skipped_packages=skipped_packages,
        )
    logger(f"Collected versions for {len(package_versions):,d} NuGet package.")
    return package_versions, skipped_packages


def get_nuget_purls_from_versions(base_purl, versions):
    """Return PURLs for a NuGet `base_purls` from set of `versions`."""
    purl_dict = PackageURL.from_string(base_purl).to_dict()
    del purl_dict["version"]
    return [PackageURL(**purl_dict, version=v).to_string() for v in versions]
