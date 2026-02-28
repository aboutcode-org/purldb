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

from minecode_pipelines.pipes import meson
from minecode_pipelines.pipelines import MineCodeBasePipeline
from scanpipe.pipes import federatedcode


class MineMeson(MineCodeBasePipeline):
    """Pipeline to mine Meson WrapDB packages and publish them to FederatedCode repo."""

    MESON_WRAPDB_REPO = "https://github.com/mesonbuild/wrapdb"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.clone_wrapdb_index,
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def clone_wrapdb_index(self):
        """Clone the Meson WrapDB repository."""
        self.wrapdb_repo = federatedcode.clone_repository(
            repo_url=self.MESON_WRAPDB_REPO,
            clone_path=self.working_path / "wrapdb",
            logger=self.log,
        )

    def packages_count(self):
        releases_path = Path(self.wrapdb_repo.working_dir) / "releases.json"
        if not releases_path.exists():
            return 0
        with open(releases_path, encoding="utf-8") as f:
            releases = json.load(f)
        return len(releases)

    def mine_packageurls(self):
        """Yield PackageURLs from Meson WrapDB releases.json."""
        return meson.mine_meson_packageurls(
            wrapdb_repo=self.wrapdb_repo,
            logger=self.log,
        )
