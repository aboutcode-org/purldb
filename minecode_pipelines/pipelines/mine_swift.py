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

from minecode_pipelines.pipelines import MineCodeBasePipeline
from minecode_pipelines.pipes.swift import mine_swift_packageurls
from minecode_pipelines.pipes.swift import load_swift_package_urls


class MineSwift(MineCodeBasePipeline):
    """
    Pipeline to mine Swift packages and publish them to FederatedCode.
    """

    swift_index_repo_url = "https://github.com/SwiftPackageIndex/PackageList"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
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

    def packages_count(self):
        return len(self.swift_packages_urls) if self.swift_packages_urls else None

    def mine_packageurls(self):
        self.swift_packages_urls = load_swift_package_urls(swift_index_repo=self.swift_index_repo)
        self.log(f"Total Swift packages to process: {len(self.swift_packages_urls)}")
        return mine_swift_packageurls(
            packages_urls=self.swift_packages_urls,
            logger=self.log,
        )
