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
from packageurl import PackageURL
from aboutcode.hashid import get_package_purls_yml_file_path
from minecode_pipelines.utils import git_stage_purls, commit_and_push_changes


def mine_and_publish_cran_packageurls(fed_repo, db_path):
    for purls in extract_cran_packages(db_path):
        if not purls:
            continue

        first_purl = purls[0]
        purl_yaml_path = get_package_purls_yml_file_path(first_purl)
        git_stage_purls(purls, fed_repo, purl_yaml_path)

    commit_and_push_changes(fed_repo)


def extract_cran_packages(json_file_path: str) -> list:
    """
    Extract package names and their versions from a CRAN DB JSON file.
    """
    db_path = Path(json_file_path)
    if not db_path.exists():
        raise FileNotFoundError(f"File not found: {db_path}")

    with open(db_path, encoding="utf-8") as f:
        data = json.load(f)

    for pkg_name, pkg_data in data.items():
        versions = list(pkg_data.get("versions", {}).keys())
        purls = []
        for version in versions:
            purl = PackageURL(
                type="cran",
                name=pkg_name,
                version=version,
            )
            purls.append(purl.to_string())
        yield purls
