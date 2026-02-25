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

from minecode_pipelines import pipes
from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipelines import _mine_and_publish_packageurls
from minecode_pipelines.pipes import crates


class MineCrates(MineCodeBasePipeline):
    """Mine PackageURLs from crates.io-index and publish them to FederatedCode."""

    pipeline_config_repo = "https://github.com/aboutcode-data/minecode-pipelines-config/"
    checkpoint_path = "crates/checkpoints.json"
    append_purls = True

    crates_index_repo_url = "https://github.com/rust-lang/crates.io-index"

    last_checkpoint = ""
    current_utc = ""

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_federation_config,
            cls.fetch_checkpoint_and_crates_io_index,
            cls.get_current_utc,
            cls.mine_and_publish_crates_packageurls,
            cls.save_check_point,
            cls.delete_working_dir,
        )

    def fetch_checkpoint_and_crates_io_index(self):
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
        )
        if checkpoint:
            self.last_checkpoint = checkpoint.get("previous_index_date")
            self.log(f"last_checkpoint: {self.last_checkpoint}")

        # Clone the crates.io-index repository
        self.crates_index_repo = federatedcode.clone_repository(
            repo_url=self.crates_index_repo_url,
            clone_path=self.working_path / "crates_index_repo",
            logger=self.log,
        )

        self.crates_collector = crates.CratesCollector(
            repo_location=self.crates_index_repo,
            logger=self.log,
        )

    def get_current_utc(self):
        from datetime import datetime, timezone

        self.current_utc = datetime.now(timezone.utc).isoformat()

    def mine_and_publish_crates_packageurls(self):
        _mine_and_publish_packageurls(
            packageurls=self.crates_collector.get_packages(
                previous_index_date=self.last_checkpoint
            ),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    def save_check_point(self):
        checkpoint = {"previous_index_date": self.current_utc}

        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
            logger=self.log,
        )
