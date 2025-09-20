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

import os
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines import pipes
from minecode_pipelines.pipes.swift import process_swift_packages

MINECODE_DATA_SWIFT_REPO = os.environ.get(
    "MINECODE_DATA_SWIFT_REPO", "https://github.com/aboutcode-data/minecode-data-swift-test"
)
MINECODE_SWIFT_INDEX_REPO = "https://github.com/SwiftPackageIndex/"


class MineandPublishSwiftPURLs(Pipeline):
    """
    Mine all packageURLs from a swift index and publish them to a FederatedCode repo.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.clone_repos,
            cls.mine_and_publish_swift_packageurls,
            cls.delete_cloned_repos,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available(logger=self.log)

    def clone_repos(self):
        """
        Clone the Swift-related repositories (index, data, and pipelines config)
        and store their Repo objects in the corresponding instance variables.
        """
        self.swift_index_repo = federatedcode.clone_repository(MINECODE_SWIFT_INDEX_REPO)
        self.cloned_data_repo = federatedcode.clone_repository(MINECODE_DATA_SWIFT_REPO)
        self.cloned_config_repo = federatedcode.clone_repository(MINECODE_PIPELINES_CONFIG_REPO)

        if self.log:
            self.log(
                f"{MINECODE_SWIFT_INDEX_REPO} repo cloned at: {self.cargo_index_repo.working_dir}"
            )
            self.log(
                f"{MINECODE_DATA_SWIFT_REPO} repo cloned at: {self.cloned_data_repo.working_dir}"
            )
            self.log(
                f"{MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {self.cloned_config_repo.working_dir}"
            )

    def mine_and_publish_swift_packageurls(self):
        """Mine swift package names from swift indexes or checkpoint."""
        process_swift_packages(self.swift_index_repo, self.cloned_data_repo, self.log)

    def delete_cloned_repos(self):
        pipes.delete_cloned_repos(
            repos=[self.swift_index_repo, self.cloned_data_repo, self.cloned_config_repo],
            logger=self.log,
        )
