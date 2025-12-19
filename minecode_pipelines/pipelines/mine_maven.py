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

from aboutcode.pipeline import optional_step
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
            cls.fetch_checkpoint_and_maven_index_repo1_maven_org,
            cls.mine_and_publish_maven_packageurls_repo1_maven_org,
            cls.save_check_point_repo1_maven_org,
            cls.fetch_checkpoint_and_maven_index_repo_spring_io_release,
            cls.mine_and_publish_maven_packageurls_repo_spring_io_release,
            cls.save_check_point_repo_spring_io_release,
            cls.fetch_checkpoint_and_maven_index_repo_spring_io_milestone,
            cls.mine_and_publish_maven_packageurls_repo_spring_io_milestone,
            cls.save_check_point_repo_spring_io_milestone,
            cls.fetch_checkpoint_and_maven_index_plugins_gradle_org,
            cls.mine_and_publish_maven_packageurls_plugins_gradle_org,
            cls.save_check_point_plugins_gradle_org,
            cls.fetch_checkpoint_and_maven_index_repository_apache_org,
            cls.mine_and_publish_maven_packageurls_repository_apache_org,
            cls.save_check_point_repository_apache_org,
            cls.delete_working_dir,
        )

    @optional_step("repo1.maven.org")
    def fetch_checkpoint_and_maven_index_repo1_maven_org(self):
        checkpoint_path = "maven/repo.maven.org/checkpoints.json"
        maven_url = "https://repo1.maven.org/maven2"
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")

        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(
            maven_url=maven_url,
            last_incremental=last_incremental,
            logger=self.log,
        )

    @optional_step("repo1.maven.org")
    def mine_and_publish_maven_packageurls_repo1_maven_org(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    @optional_step("repo1.maven.org")
    def save_check_point_repo1_maven_org(self):
        checkpoint_path = "maven/repo.maven.org/checkpoints.json"
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )

    @optional_step("repo.spring.io/release")
    def fetch_checkpoint_and_maven_index_repo_spring_io_release(self):
        checkpoint_path = "maven/repo.spring.io/release/checkpoints.json"
        maven_url = "https://repo.spring.io/artifactory/release"
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")

        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(
            maven_url=maven_url,
            last_incremental=last_incremental,
            logger=self.log,
        )

    @optional_step("repo.spring.io/release")
    def mine_and_publish_maven_packageurls_repo_spring_io_release(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    @optional_step("repo.spring.io/release")
    def save_check_point_repo_spring_io_release(self):
        checkpoint_path = "maven/repo.spring.io/release/checkpoints.json"
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )

    @optional_step("repo.spring.io/milestone")
    def fetch_checkpoint_and_maven_index_repo_spring_io_milestone(self):
        checkpoint_path = "maven/repo.spring.io/milestone/checkpoints.json"
        maven_url = "https://repo.spring.io/artifactory/milestone"
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")

        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(
            maven_url=maven_url,
            last_incremental=last_incremental,
            logger=self.log,
        )

    @optional_step("repo.spring.io/milestone")
    def mine_and_publish_maven_packageurls_repo_spring_io_milestone(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    @optional_step("plugins.gradle.org")
    def save_check_point_repo_spring_io_milestone(self):
        checkpoint_path = "maven/repo.spring.io/milestone/checkpoints.json"
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )

    @optional_step("plugins.gradle.org")
    def fetch_checkpoint_and_maven_index_plugins_gradle_org(self):
        checkpoint_path = "maven/plugins.gradle.org/checkpoints.json"
        maven_url = "https://plugins.gradle.org/m2"
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")

        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(
            maven_url=maven_url,
            last_incremental=last_incremental,
            logger=self.log,
        )

    @optional_step("plugins.gradle.org")
    def mine_and_publish_maven_packageurls_plugins_gradle_org(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    @optional_step("plugins.gradle.org")
    def save_check_point_plugins_gradle_org(self):
        checkpoint_path = "maven/plugins.gradle.org/checkpoints.json"
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )

    @optional_step("repository.apache.org")
    def fetch_checkpoint_and_maven_index_repository_apache_org(self):
        checkpoint_path = "maven/repository.apache.org/checkpoints.json"
        maven_url = "https://repository.apache.org/snapshots"
        self.checkpoint_config_repo = federatedcode.clone_repository(
            repo_url=self.pipeline_config_repo,
            clone_path=self.working_path / "minecode-pipelines-config",
            logger=self.log,
        )
        checkpoint = pipes.get_checkpoint_from_file(
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
        )

        last_incremental = checkpoint.get("last_incremental")

        self.log(f"last_incremental: {last_incremental}")
        self.maven_nexus_collector = maven.MavenNexusCollector(
            maven_url=maven_url,
            last_incremental=last_incremental,
            logger=self.log,
        )

    @optional_step("repository.apache.org")
    def mine_and_publish_maven_packageurls_repository_apache_org(self):
        _mine_and_publish_packageurls(
            packageurls=self.maven_nexus_collector.get_packages(),
            total_package_count=None,
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    @optional_step("repository.apache.org")
    def save_check_point_repository_apache_org(self):
        checkpoint_path = "maven/repository.apache.org/checkpoints.json"
        last_incremental = self.maven_nexus_collector.index_properties.get(
            "nexus.index.last-incremental"
        )
        checkpoint = {"last_incremental": last_incremental}
        self.log(f"Saving checkpoint: {checkpoint}")
        pipes.update_checkpoints_in_github(
            checkpoint=checkpoint,
            cloned_repo=self.checkpoint_config_repo,
            path=checkpoint_path,
            logger=self.log,
        )
