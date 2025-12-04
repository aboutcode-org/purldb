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

from minecode_pipelines.pipes import cargo
from minecode_pipelines.pipelines import MineCodeBasePipeline
from scanpipe.pipes import federatedcode


class MineCargo(MineCodeBasePipeline):
    """Pipeline to mine Cargo (crates.io) packages and publish them to FederatedCode."""

    MINECODE_CARGO_INDEX_REPO = "https://github.com/rust-lang/crates.io-index"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.clone_cargo_index,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def clone_cargo_index(self):
        """Clone the Cargo index Repo."""
        self.cargo_index_repo = federatedcode.clone_repository(
            repo_url=self.MINECODE_CARGO_INDEX_REPO,
            clone_path=self.working_path / "crates.io-index",
            logger=self.log,
        )

    def packages_count(self):
        base_path = Path(self.cargo_index_repo.working_tree_dir)
        package_dir = [p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
        return sum(1 for dir in package_dir for f in dir.rglob("*") if f.is_file())

    def mine_packageurls(self):
        """Yield PackageURLs from Cargo index."""
        return cargo.mine_cargo_packageurls(
            cargo_index_repo=self.cargo_index_repo,
            logger=self.log,
        )
