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

from git.repo.base import Repo
from scanpipe.pipes.federatedcode import delete_local_clone
from minecode.utils import get_temp_file
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode
from minecode_pipelines.miners import cargo


class MineandPublishCargoPURLs(Pipeline):
    """Pipeline to mine Cargo (crates.io) packages and publish them to FederatedCode."""

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.clone_cargo_repo,
            cls.collect_packages_from_cargo,
            cls.clean_cargo_repo,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_eligibility(project=self.project)

    def clone_cargo_repo(self):
        """
        Clone the repo at repo_url and return the VCSResponse object
        """
        conan_repo_url = "git+https://github.com/rust-lang/crates.io-index"
        fed_repo_url = "git+https://github.com/ziadhany/cargo-test"

        self.fed_repo = federatedcode.clone_repository(fed_repo_url)
        self.cargo_repo = Repo.clone_from(conan_repo_url, get_temp_file())

    def collect_packages_from_cargo(self):
        cargo.process_cargo_packages(self.cargo_repo, self.fed_repo)

    def clean_cargo_repo(self):
        """
        Delete the federatedcode repository if it exists, and also delete the Cargo repository if it exists.
        """
        if self.cargo_repo:
            delete_local_clone(self.cargo_repo)

        if self.fed_repo:
            delete_local_clone(self.fed_repo)
