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

from datetime import datetime
from scanpipe.pipes import federatedcode

from minecode_pipelines import pipes
from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipes.swift import PACKAGE_BATCH_SIZE, mine_swift_packageurls
from minecode_pipelines.pipes.swift import load_swift_package_urls
from minecode_pipelines.pipelines import _mine_and_publish_packageurls


class MineSwift(MineCodeBasePipeline):
    """
    Pipeline to mine Swift packages and publish them to FederatedCode.
    """

    pipeline_config_repo = "https://github.com/aboutcode-data/minecode-pipelines-config/"
    checkpoint_path = "swift/checkpoints.json"
    checkpoint_freq = 200
    swift_index_repo_url = "https://github.com/SwiftPackageIndex/PackageList"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_checkpoint_and_start_index,
            cls.fetch_federation_config,
            cls.clone_swift_index,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def clone_swift_index(self):
        """Clone the Cargo index Repo."""
        self.swift_index_repo = federatedcode.clone_repository(
            repo_url=self.swift_index_repo_url,
            clone_path=self.working_path / "swift-index",
            logger=self.log,
        )

    def fetch_checkpoint_and_start_index(self):
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
        )

        self.start_index = checkpoint.get("start_index", 0)
        self.log(f"start_index: {self.start_index}")

    def packages_count(self):
        return len(self.swift_packages_urls) if self.swift_packages_urls else None

    def mine_packageurls(self):
        self.swift_packages_urls = load_swift_package_urls(swift_index_repo=self.swift_index_repo)
        return mine_swift_packageurls(
            packages_urls=self.swift_packages_urls,
            start_index=self.start_index,
            logger=self.log,
        )

    def mine_and_publish_packageurls(self):
        """Mine and publish PackageURLs."""
        _mine_and_publish_packageurls(
            packageurls=self.mine_packageurls(),
            total_package_count=self.packages_count(),
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
            checkpoint_func=self.save_check_point,
            checkpoint_freq=self.checkpoint_freq,
        )

    def save_check_point(self):
        checkpoint = {
            "date": str(datetime.now()),
            "start_index": self.start_index + self.checkpoint_freq * PACKAGE_BATCH_SIZE,
        }

        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
            logger=self.log,
        )
