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
import json
from pathlib import Path

from minecode_pipeline.pipes import cargo

from scanpipe.pipelines import Pipeline
from fetchcode.vcs import fetch_via_vcs
from scanpipe.pipes import federatedcode


class MineCargo(Pipeline):
    """Pipeline to mine Cargo (crates.io) packages and publish them to FederatedCode."""

    repo_url = "git+https://github.com/rust-lang/crates.io-index"

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.clone_cargo_repo,
            cls.collect_packages_from_cargo,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_eligibility(project=self.project)

    def clone_cargo_repo(self, repo_url):
        """
        Clone the repo at repo_url and return the VCSResponse object
        """
        self.vcs_response = fetch_via_vcs(repo_url)

    def collect_packages_from_cargo(self):
        base_path = Path(self.vcs_response.dest_dir)

        json_files = []
        for file_path in base_path.glob("**/*"):
            if not file_path.is_file():
                continue
            if file_path.name in {"config.json", "README.md", "update-dl-url.yml"}:
                continue
            json_files.append(file_path)

        for idx, file_path in enumerate(json_files, start=1):
            try:
                with open(file_path, encoding="utf-8") as f:
                    packages = []
                    for line in f:
                        if line.strip():
                            packages.append(json.loads(line))

            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if packages:
                push_commit = idx == len(json_files)  # only True on last
                cargo.collect_packages_from_cargo(packages, self.vcs_response, push_commit)

    def clean_cargo_repo(self):
        """
        Delete the VCS response repository if it exists.
        """
        if self.vcs_response:
            self.vcs_response.delete()
