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


from minecode_pipelines.pipes import apache
from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipelines import _mine_and_publish_packageurls


class MineApache(MineCodeBasePipeline):
    """Mine PackageURLs from apache.org and publish them to FederatedCode."""

    package_batch_size = 5

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.mine_apache_packages,
            cls.get_apache_packages_to_sync,
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.update_mined_checkpoints,
            cls.delete_working_dir,
        )

    def mine_apache_packages(self):
        """Mine apache package archive path from the find_ls file or checkpoint."""
        (self.apache_packages, self.apache_packages_metadata, self.config_repo) = (
            apache.mine_apache_packages(logger=self.log)
        )

    def get_apache_packages_to_sync(self):
        """Get apache packages which needs to be synced using checkpoint."""
        self.packages, self.synced_packages = apache.get_apache_packages_to_sync(
            packages_file=self.apache_packages,
            logger=self.log,
        )

    def packages_count(self):
        return len(self.packages)

    def mine_packageurls(self):
        """Yield npm packageURLs for all mined npm package names."""
        self.packages_mined = []
        yield from apache.mine_and_publish_apache_packageurls(
            packages_to_sync=self.packages,
            packages_mined=self.packages_mined,
            packages_metadata=self.apache_packages_metadata,
            logger=self.log,
        )

    def save_check_point(self):
        apache.save_mined_packages_in_checkpoint(
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

    def update_mined_checkpoints(self):
        apache.update_mined_checkpoints(
            config_repo=self.config_repo,
            logger=self.log,
        )
