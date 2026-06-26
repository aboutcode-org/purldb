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
from minecode_pipelines.pipes import apache

from datetime import datetime, timezone


class MineApache(MineCodeBasePipeline):
    """Mine PackageURLs from apache.org and publish them to FederatedCode."""

    pipeline_config_repo = "https://github.com/aboutcode-data/minecode-pipelines-config/"

    append_purls = True

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_federation_config,
            cls.fetch_checkpoint_config_repo,
            cls.fetch_apache,
            cls.mine_and_publish_apache_packageurls,
            cls.save_check_point,
            cls.delete_working_dir,
        )

    def fetch_checkpoint_config_repo(self):
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )

    def fetch_apache(self):
        checkpoint_path = "apache/checkpoints.json"
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )
        last_sync = checkpoint.get("last_sync", "")
        if last_sync:
            self.log(f"last_sync: {last_sync}")
        find_ls_url = "https://archive.apache.org/dist/zzz/find-ls2.txt.gz"
        project_json = "https://projects.apache.org/json/foundation/projects.json"
        self.apache_collector = apache.ApacheCollector(
            find_ls_url=find_ls_url,
            project_json=project_json,
            logger=self.log,
        )

    def mine_and_publish_apache_packageurls(self):
        _mine_and_publish_packageurls(
            packageurls=self.apache_collector.get_packages(),
            total_package_count=None,
            data_clusters=self.data_clusters,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    def save_check_point(self):
        checkpoint_path = "apache/checkpoints.json"
        # We use the current timestamp to record when the sync occurred.
        now = datetime.now(timezone.utc)
        checkpoint = {"last_sync": now}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )
