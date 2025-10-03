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

from matchcode_pipeline import pipes
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines.pipes.composer import mine_composer_packages
from minecode_pipelines.pipes.composer import mine_and_publish_composer_purls

MINECODE_COMPOSER_GIT_URL = os.environ.get(
    "MINECODE_COMPOSER_GIT_URL", "https://github.com/aboutcode-data/minecode-data-composer-test"
)


class MineComposer(Pipeline):
    """
    Mine all packageURLs from a composer index and publish them to a FederatedCode repo.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.clone_composer_repo,
            cls.mine_and_publish_composer_purls,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available(logger=self.log)

    def clone_composer_repo(self):
        """
        Clone the federatedcode composer url and return the Repo object
        """
        self.cloned_data_repo = federatedcode.clone_repository(MINECODE_COMPOSER_GIT_URL)
        self.cloned_config_repo = federatedcode.clone_repository(MINECODE_PIPELINES_CONFIG_REPO)

    def mine_and_publish_composer_purls(self):
        """
        Mine Composer package names from Composer indexes and generate
        package URLs (pURLs) for all mined Composer packages.
        """

        composer_packages = mine_composer_packages()
        mine_and_publish_composer_purls(
            packages=composer_packages,
            cloned_data_repo=self.cloned_data_repo,
            cloned_config_repo=self.cloned_config_repo,
            logger=self.log,
        )

    def delete_cloned_repos(self):
        pipes.delete_cloned_repos(
            repos=[self.cloned_data_repo, self.cloned_config_repo],
            logger=self.log,
        )
