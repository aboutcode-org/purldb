#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import requests
from dateutil import parser
from packagedcode.models import PackageData
from packageurl import PackageURL


TRACE = False
TRACE_DEEP = False

CRATES_API_URL = "https://crates.io/api/v1/crates/"


class CratesCollector:
    def __init__(
        self,
        repo_location=None,
        logger=None,
    ):
        if not repo_location:
            raise Exception("repo_location must be set for CratesCollector.")
        self.repo_location = repo_location

    def get_packages(self, previous_index_date=None, logger=None):
        """Yield Package objects from crates.io-index"""
        base_dir = self.repo_location.working_dir

        previous_index_date_parsed = ""
        if previous_index_date:
            previous_index_date_parsed = parser.isoparse(previous_index_date)

        for root, dirs, filenames in os.walk(base_dir):
            # Skip .github and .git directories at the top level
            if root == base_dir:
                dirs.remove(".github")
                dirs.remove(".git")
                # Skip README.md and config.json at the top level
                filenames = [f for f in filenames if f not in ("README.md", "config.json")]

            for crate_name in filenames:
                url = f"{CRATES_API_URL}/{crate_name}"
                response = requests.get(url)
                if not response.status_code == 200:
                    self.logger(f"Error fetching {crate_name}: {response.status_code}")
                else:
                    data = response.json()
                    crate_versions_info = data.get("versions", {})
                    for crate_version_info in crate_versions_info:
                        package_last_update = crate_version_info.get("updated_at", "")
                        if previous_index_date_parsed and package_last_update:
                            last_update = parser.isoparse(package_last_update)
                            if last_update < previous_index_date_parsed:
                                continue
                        name = crate_version_info.get("crate")
                        version = crate_version_info.get("num")
                        download_url = "https://crates.io" + crate_version_info.get("dl_path", "")
                        release_date = crate_version_info.get("created_at", "")
                        sha256 = crate_version_info.get("checksum", "")
                        homepage_url = crate_version_info.get("homepage", "")
                        if not homepage_url:
                            homepage_url = crate_version_info.get("repository", "")

                        package = PackageData(
                            type="maven",
                            namespace=None,
                            name=name,
                            version=version,
                            qualifiers=None,
                            download_url=download_url,
                            sha256=sha256,
                            release_date=release_date,
                            repository_homepage_url=homepage_url,
                            repository_download_url=download_url,
                        )
                        current_purl = PackageURL(
                            type="maven",
                            name=name,
                            version=version,
                        )
                        yield current_purl, [package.purl]
