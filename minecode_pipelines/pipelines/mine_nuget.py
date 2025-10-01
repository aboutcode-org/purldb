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


from pathlib import Path

from minecode_pipelines.pipes import nuget

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode


class MineNuGet(Pipeline):
    """
    Mine and Publish NuGet PackageURLs.

    Mine PackageURLs from AboutCode NuGet catalog mirror and publish
    them to FederatedCode Git repository.
    """

    download_inputs = False
    CATALOG_REPO_URL = "https://github.com/aboutcode-org/aboutcode-mirror-nuget-catalog.git"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.fetch_nuget_catalog,
            cls.mine_nuget_package_versions,
            cls.mine_and_publish_nuget_packageurls,
            cls.delete_cloned_repos,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available()

    def fetch_nuget_catalog(self):
        """Fetch NuGet package catalog from AboutCode mirror."""
        self.catalog_repo = federatedcode.clone_repository(
            repo_url=self.CATALOG_REPO_URL,
            logger=self.log,
        )

    def mine_nuget_package_versions(self):
        """Mine NuGet package and versions from NuGet catalog."""
        self.package_versions, self.skipped_packages = nuget.mine_nuget_package_versions(
            catalog_path=Path(self.catalog_repo.working_dir),
            logger=self.log,
        )

    def mine_and_publish_nuget_packageurls(self):
        """Mine and publish PackageURLs from NuGet package versions."""
        nuget.mine_and_publish_nuget_packageurls(
            package_versions=self.package_versions,
            logger=self.log,
        )

    def delete_cloned_repos(self):
        """Remove cloned catalog repository."""
        if self.catalog_repo:
            self.log("Removing cloned repository")
            federatedcode.delete_local_clone(repo=self.catalog_repo)
