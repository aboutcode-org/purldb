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

import requests

from minecode_pipelines.pipes import meson
from minecode_pipelines.pipelines import MineCodeBasePipeline


class MineMeson(MineCodeBasePipeline):
    """Pipeline to mine Meson WrapDB packages and publish them to FederatedCode repo."""

    MESON_WRAPDB_RELEASES_URL = (
        "https://raw.githubusercontent.com/mesonbuild/wrapdb/master/releases.json"
    )

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_wrapdb_releases,
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def fetch_wrapdb_releases(self):
        """Fetch the Meson WrapDB releases.json index."""
        try:
            response = requests.get(self.MESON_WRAPDB_RELEASES_URL, timeout=30)
            response.raise_for_status()
            self.releases = response.json()
        except Exception as e:
            self.log(f"Failed to fetch releases.json: {e}")
            self.releases = {}

    def packages_count(self):
        """Return the number of packages in the WrapDB releases index.

        Used by MineCodeBasePipeline to report mining progress.
        """
        return len(self.releases) if hasattr(self, "releases") and self.releases else 0

    def mine_packageurls(self):
        """Yield PackageURLs from Meson WrapDB releases.json."""
        return meson.mine_meson_packageurls(releases=self.releases, logger=self.log)
