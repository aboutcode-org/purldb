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

from aboutcode.hashid import get_package_purls_yml_file_path, get_core_purl
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from minecode_pipelines.miners.cran import extract_cran_packages
from minecode_pipelines.pipes import write_data_to_yaml_file
from minecode_pipelines.utils import grouper

PACKAGE_BATCH_SIZE = 1000


def mine_and_publish_cran_packageurls(cloned_data_repo, db_path, logger):
    """
    Extract CRAN packages from the database, write their package URLs (purls) to YAML,
    and commit changes in batches to the given cloned repository.
    """
    packages_to_sync = list(extract_cran_packages(db_path))

    for package_batch in grouper(packages_to_sync, PACKAGE_BATCH_SIZE):
        purl_files = []
        base_purls = []

        if logger:
            logger(f"Starting package mining for a batch of {PACKAGE_BATCH_SIZE} packages")

        for updated_purls in package_batch:
            if not updated_purls:
                continue  # skip padded None values or empty

            first_purl = updated_purls[0]
            base_purl = get_core_purl(first_purl)
            purl_yaml_path = cloned_data_repo.working_dir / get_package_purls_yml_file_path(
                first_purl
            )
            write_data_to_yaml_file(path=purl_yaml_path, data=updated_purls)

            logger(f"writing packageURLs for package: {str(base_purl)} at: {purl_yaml_path}")
            purl_files.append(purl_yaml_path)
            base_purls.append(str(base_purl))

        # After finishing the batch, commit & push if there’s something to save
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
