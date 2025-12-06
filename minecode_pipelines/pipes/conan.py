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

from pathlib import Path
from packageurl import PackageURL

from minecode import saneyaml


def get_conan_packages(package_name, versions):
    base_purl = PackageURL(type="conan", name=package_name)

    updated_purls = []
    for version in versions:
        version_str = version.get("version")
        purl = PackageURL(type="conan", name=package_name, version=version_str).to_string()
        updated_purls.append(purl)
    return base_purl, updated_purls


def mine_conan_packageurls(conan_index_repo, logger):
    """Mine Conan PackageURLs from package index."""

    base_path = Path(conan_index_repo.working_dir)
    for file_path in base_path.glob("recipes/**/*"):
        if not file_path.name == "config.yml":
            continue
        # Example: file_path = Path("repo_path/recipes/7zip/config.yml")
        # - file_path.parts = ("repo_path", "recipes", "7zip", "config.yml")
        # - file_path.parts[-2] = "7zip"  (the package name)
        package = file_path.parts[-2]
        with open(file_path, encoding="utf-8") as f:
            versions = saneyaml.load(f)

        if not versions:
            continue

        yield get_conan_packages(package, versions)
