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

from datetime import datetime
from pathlib import Path
from aboutcode import hashid
from aboutcode.hashid import get_package_base_dir
from minecode_pipelines.miners.composer import get_composer_packages
from minecode_pipelines.miners.composer import load_composer_packages
from minecode_pipelines.miners.composer import get_composer_purl
from minecode_pipelines.pipes import (
    write_data_to_yaml_file,
    get_checkpoint_from_file,
    update_checkpoints_in_github,
)
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from minecode_pipelines.utils import cycle_from_index, grouper

PACKAGE_BATCH_SIZE = 100
COMPOSER_CHECKPOINT_PATH = "composer/checkpoints.json"


def mine_composer_packages():
    """Mine Composer package names from Packagist and return List of (vendor, package) tuples."""
    packages_file = get_composer_packages()
    return load_composer_packages(packages_file)


def mine_and_publish_composer_purls(packages, cloned_data_repo, cloned_config_repo, logger):
    """Mine Composer packages and publish their PURLs to a FederatedCode repository."""
    composer_checkpoint = get_checkpoint_from_file(
        cloned_repo=cloned_config_repo, path=COMPOSER_CHECKPOINT_PATH
    )

    start_index = composer_checkpoint.get("start_index", 0)

    packages_iter = cycle_from_index(packages, start_index)

    for batch_index, package_batch in enumerate(
        grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_iter)
    ):
        purl_files = []
        purls = []

        for item in package_batch:
            if not item:
                continue

            vendor, package = item
            logger(f"getting packageURLs for package: {vendor}/{package}")

            updated_purls = get_composer_purl(vendor=vendor, package=package)
            if not updated_purls:
                continue

            base_purl = updated_purls[0]
            package_base_dir = get_package_base_dir(purl=base_purl)

            logger(f"writing packageURLs for package: {base_purl} at: {package_base_dir}")
            logger(f"packageURLs: {' '.join(updated_purls)}")

            purl_file_full_path = Path(
                cloned_data_repo.working_dir
            ) / hashid.get_package_purls_yml_file_path(base_purl)

            write_data_to_yaml_file(path=purl_file_full_path, data=updated_purls)

            purl_files.append(purl_file_full_path)
            purls.append(str(base_purl))

        if purl_files:
            commit_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                purls=purls,
                mine_type="packageURL",
                tool_name="pkg:composer/minecode-pipelines",
                tool_version=VERSION,
            )
            push_changes(repo=cloned_data_repo)

            settings_data = {
                "date": str(datetime.now()),
                "start_index": start_index + (batch_index + 1) * PACKAGE_BATCH_SIZE,
            }
            update_checkpoints_in_github(
                checkpoint=settings_data,
                cloned_repo=cloned_config_repo,
                path=COMPOSER_CHECKPOINT_PATH,
            )
