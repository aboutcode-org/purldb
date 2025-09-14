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
from minecode_pipelines.pipes.composer import mine_composer_packages
from minecode_pipelines.pipes.composer import mine_and_publish_composer_purls

FEDERATEDCODE_COMPOSER_GIT_URL = os.environ.get(
    "FEDERATEDCODE_COMPOSER_GIT_URL", "https://github.com/ziadhany/composer-test"
)


class MineandPublishComposerPURLs(Pipeline):
    """
    Mine all packageURLs from a composer index and publish them to a FederatedCode repo.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.clone_fed_repo,
            cls.mine_composer_packages,
            cls.mine_and_publish_composer_purls,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_eligibility(project=self.project)

    def clone_fed_repo(self):
        """
        Clone the federatedcode composer url and return the Repo object
        """
        self.fed_repo = federatedcode.clone_repository(FEDERATEDCODE_COMPOSER_GIT_URL)

    def mine_composer_packages(self):
        """Mine composer package names from composer indexes."""
        self.composer_packages = mine_composer_packages(logger=self.log)

    def mine_and_publish_composer_purls(self):
        """Get composer packageURLs for all mined composer package names."""
        mine_and_publish_composer_purls(
            packages=self.composer_packages, fed_repo=self.fed_repo, logger=self.log
        )
