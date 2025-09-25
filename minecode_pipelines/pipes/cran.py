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
from aboutcode.hashid import get_package_purls_yml_file_path, get_core_purl

from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from minecode_pipelines.pipes import write_data_to_yaml_file

PACKAGE_BATCH_SIZE = 1000


def mine_and_publish_cran_packageurls(cloned_data_repo, db_path, logger):
    """
    Extract CRAN packages from the database, write their package URLs (purls) to YAML,
    and commit changes in batches to the given cloned repository.
    """
    batch_counter = 0
    purl_files = []
    base_purls = []

    for updated_purls in extract_cran_packages(db_path):
        batch_counter += 1
        if not updated_purls:
            continue

        first_purl = updated_purls[0]
        base_purl = get_core_purl(first_purl)
        purl_yaml_path = cloned_data_repo.working_dir / get_package_purls_yml_file_path(first_purl)
        write_data_to_yaml_file(path=purl_yaml_path, data=updated_purls)

        logger(f"writing packageURLs for package: {str(base_purl)} at: {purl_yaml_path}")
        purl_files.append(purl_yaml_path)
        base_purls.append(str(base_purl))

        if purl_files and base_purls and batch_counter > PACKAGE_BATCH_SIZE:
            commit_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                purls=base_purls,
                mine_type="packageURL",
                tool_name="pkg:pypi/minecode-pipelines",
                tool_version=VERSION,
            )
            push_changes(repo=cloned_data_repo)

            batch_counter = 0
            purl_files.clear()
            base_purls.clear()

    if purl_files and base_purls:
        commit_changes(
            repo=cloned_data_repo,
            files_to_commit=purl_files,
            purls=base_purls,
            mine_type="packageURL",
            tool_name="pkg:pypi/minecode-pipelines",
            tool_version=VERSION,
        )
        push_changes(repo=cloned_data_repo)


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
