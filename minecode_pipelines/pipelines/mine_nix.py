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

from scanpipe.pipes import federatedcode

from minecode_pipelines.pipes import nix
from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipelines import _mine_and_publish_packageurls


class MineNix(MineCodeBasePipeline):
    """
    Mine PackageURLs from NixOS-Packages and publish them to FederatedCode.
    """

    package_batch_size = 5
    nixpkgs_repo_url = "https://github.com/NixOS/nixpkgs"

    @classmethod
    def steps(cls):
        return (
            cls.check_nix_availability,
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_nixpkgs_repo,
            cls.mine_nix_packages,
            cls.get_nixpkgs_packages_to_sync,
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.update_state_and_checkpoints,
            cls.delete_working_dir,
        )

    def check_nix_availability(self):
        """Check if Nix is available on the system."""
        nix.check_nix_availability(logger=self.log)

    def fetch_nixpkgs_repo(self):
        """Fetch the Nixpkgs repository."""
        self.nixpkgs_repo = federatedcode.clone_repository(
            repo_url=self.nixpkgs_repo_url,
            clone_path=self.working_path / "nixpkgs_repo",
            logger=self.log,
        )

    def mine_nix_packages(self):
        """Mine Nix package names from NixOS packages or checkpoint."""
        (self.nix_packages, self.state, self.last_seq, self.config_repo) = nix.mine_nix_packages(
            nixpkgs_repo=self.nixpkgs_repo, logger=self.log
        )

    def get_nixpkgs_packages_to_sync(self):
        """Get Nixpkgs packages which needs to be synced using checkpoint."""
        self.packages, self.synced_packages = nix.get_nix_packages_to_sync(
            packages_file=self.nix_packages,
            state=self.state,
            logger=self.log,
        )

    def packages_count(self):
        return len(self.packages)

    def mine_packageurls(self):
        """Yield Nix packageURLs for all mined Nix package names."""
        self.packages_mined = []
        yield from nix.mine_and_publish_nix_packageurls(
            nixpkgs_repo=self.nixpkgs_repo,
            packages_to_sync=self.packages,
            packages_mined=self.packages_mined,
            logger=self.log,
        )

    def save_check_point(self):
        nix.save_mined_packages_in_checkpoint(
            packages_mined=self.packages_mined,
            synced_packages=self.synced_packages,
            config_repo=self.config_repo,
            logger=self.log,
        )
        self.packages_mined = []

    def mine_and_publish_packageurls(self):
        """Mine and publish PackageURLs."""

        _mine_and_publish_packageurls(
            packageurls=self.mine_packageurls(),
            total_package_count=self.packages_count(),
            data_clusters=self.data_clusters,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
            checkpoint_func=self.save_check_point,
            checkpoint_on_commit=True,
            batch_size=self.package_batch_size,
        )

    def update_state_and_checkpoints(self):
        nix.update_state_and_checkpoints(
            state=self.state,
            last_seq=self.last_seq,
            config_repo=self.config_repo,
            logger=self.log,
        )
