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

from minecode_pipelines import pipes
from minecode_pipelines.miners.cran import fetch_cran_db
from minecode_pipelines.pipes import cran


MINECODE_DATA_CRAN_REPO = os.environ.get(
    "MINECODE_DATA_CRAN_REPO", "https://github.com/aboutcode-data/minecode-data-cran-test"
)


class MineCran(Pipeline):
    """
    Mine all packageURLs from a CRAN R index and publish them to a FederatedCode repo.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.setup_federatedcode_cran,
            cls.mine_and_publish_cran_packageurls,
            cls.cleanup_db_and_repo,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available(logger=self.log)

    def setup_federatedcode_cran(self):
        """
        Clone the FederatedCode CRAN repository and download the CRAN DB JSON file.
        """
        self.cloned_data_repo = federatedcode.clone_repository(MINECODE_DATA_CRAN_REPO)
        self.db_path = fetch_cran_db()

        if self.log:
            self.log(
                f"{MINECODE_DATA_CRAN_REPO} repo cloned at: {self.cloned_data_repo.working_dir}"
            )

    def mine_and_publish_cran_packageurls(self):
        """Get cran packageURLs for all mined cran package names."""
        cran.mine_and_publish_cran_packageurls(
            cloned_data_repo=self.cloned_data_repo, db_path=self.db_path, logger=self.log
        )

    def cleanup_db_and_repo(self):
        self.log(f"Cleaning database file at: {self.db_path}")
        os.remove(self.db_path)

        self.log(
            f"Deleting cloned repo {MINECODE_DATA_CRAN_REPO} from: {self.cloned_data_repo.working_dir}"
        )
        pipes.delete_cloned_repos(
            repos=[self.cloned_data_repo],
            logger=self.log,
        )
