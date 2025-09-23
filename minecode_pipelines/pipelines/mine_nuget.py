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

from minecode_pipelines.pipes import nuget
from minecode_pipelines.pipes import write_packageurls_to_file
from packageurl import PackageURL

from aboutcode.hashid import get_package_base_dir
from aboutcode.pipeline import LoopProgress
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode


class MineAndPublishNuGetPURLs(Pipeline):
    """
    Mine all packageURLs from NuGet catalog and publish them to
    a FederatedCode repo.
    """

    download_inputs = False
    CATALOG_REPO_URL = (
        "https://github.com/aboutcode-org/aboutcode-mirror-nuget-catalog.git"
    )
    NUGET_PURL_METADATA_REPO = "https://github.com/aboutcode-data/minecode-data-nuget-test"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.fetch_nuget_catalog,
            cls.mine_nuget_package_versions,
            cls.mine_and_publish_nuget_packageurls,
            cls.clean_downloads,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available()

    def fetch_nuget_catalog(self):
        self.catalog_repo = federatedcode.clone_repository(
            repo_url=self.CATALOG_REPO_URL,
            logger=self.log,
        )

    def mine_nuget_package_versions(self):
        """Mine NuGet package and versions from NuGet catalog."""
        catalog = Path(self.catalog_repo.working_dir) / "catalog"
        catalog_count = nuget.get_catalog_page_count(catalog / "index.json")
        catalog_pages = catalog / "pages"

        self.package_versions = {}
        self.skipped_packages = set()
        self.log(f"Collecting versions from {catalog_count:,d} NuGet catalog.")
        progress = LoopProgress(total_iterations=catalog_count, logger=self.log)
        for page in progress.iter(catalog_pages.rglob("*.json")):
            with page.open("r", encoding="utf-8") as f:
                page_catalog = json.load(f)

            nuget.collect_package_versions(
                events=page_catalog["items"],
                package_versions=self.package_versions,
                skipped_packages=self.skipped_packages,
            )
        self.log(
            f"Collected versions for {len(self.package_versions):,d} NuGet package."
        )

    def mine_and_publish_nuget_packageurls(self):
        cloned_repo = federatedcode.clone_repository(
            repo_url=self.NUGET_PURL_METADATA_REPO,
            logger=self.log,
        )
        file_to_commit = []
        batch_size = 4000
        file_processed = 0
        nuget_package_count = len(self.package_versions)
        progress = LoopProgress(
            total_iterations=nuget_package_count,
            logger=self.log,
            progress_step=1,
        )

        self.log(f"Mine packageURL for {nuget_package_count:,d} NuGet packages.")
        for base, versions in progress.iter(self.package_versions.items()):
            package_base_dir = get_package_base_dir(purl=base)
            purl_dict = PackageURL.from_string(base).to_dict()
            del purl_dict["version"]
            packageurls = [
                PackageURL(**purl_dict, version=v).to_string() for v in versions
            ]
            purl_file = write_packageurls_to_file(
                repo=cloned_repo,
                base_dir=package_base_dir,
                packageurls=sorted(packageurls),
            )
            file_to_commit.append(purl_file)
            file_processed += 1

            if len(file_to_commit) > batch_size:
                federatedcode.commit_and_push_changes(
                    commit_message=nuget.commit_message(),
                    repo=cloned_repo,
                    files_to_commit=file_to_commit,
                    logger=self.log,
                )
                file_to_commit.clear()

        self.log(f"Processed packageURL for {file_processed:,d} NuGet packages.")
        federatedcode.commit_and_push_changes(
            commit_message=nuget.commit_message(),
            repo=cloned_repo,
            files_to_commit=file_to_commit,
            logger=self.log,
        )
        federatedcode.delete_local_clone(repo=cloned_repo)

    def clean_downloads(self):
        if self.catalog_repo:
            self.log("Removing cloned repository")
            federatedcode.delete_local_clone(repo=self.catalog_repo)
