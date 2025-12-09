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
from minecode_pipelines.pipes import maven


class MineMaven(MineCodeBasePipeline):
    """Mine PackageURLs from maven index and publish them to FederatedCode."""

    pipeline_config_repo = "https://github.com/aboutcode-data/minecode-pipelines-config/"
    checkpoint_path = "maven/checkpoints.json"
    append_purls = True

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.fetch_federation_config,
            cls.fetch_checkpoint_and_maven_index,
            cls.mine_and_publish_alpine_packageurls,
            cls.delete_working_dir,
        )

    def fetch_checkpoint_and_maven_index(self):
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")
        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(last_incremental=last_incremental)

    def mine_and_publish_alpine_packageurls(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
            checkpoint_func=self.save_check_point,
        )

    def save_check_point(self):
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=self.checkpoint_path,
            logger=self.log,
        )
