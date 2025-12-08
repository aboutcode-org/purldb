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
from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipes import cran
from minecode_pipelines.pipes.cran import fetch_cran_db


class MineCran(MineCodeBasePipeline):
    """Pipeline to mine CRAN R packages and publish them to FederatedCode."""

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def fetch_cran_db(self):
        """
        Download the full CRAN package database
        """
        self.db_path = fetch_cran_db(logger=self.log)

    def packages_count(self):
        """
        Return the count of packages found in the downloaded CRAN JSON database.
        """
        if not getattr(self, "db_path", None) or not self.db_path.exists():
            return None

        with open(self.db_path, encoding="utf-8") as f:
            return sum(1 for _ in json.load(f))

    def mine_packageurls(self):
        """Mine Cran PackageURLs from cran package database."""
        cran.mine_cran_packageurls(db_path=self.db_path)
