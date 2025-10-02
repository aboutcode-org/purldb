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
import os
from datetime import datetime
from pathlib import Path
from aboutcode import hashid
from aboutcode.hashid import get_core_purl
from packageurl import PackageURL
from purl2vcs.find_source_repo import get_tags_and_commits_from_git_output

from minecode_pipelines.miners.swift import fetch_git_tags_raw
from minecode_pipelines.miners.swift import split_org_repo

from minecode_pipelines.pipes import update_checkpoints_in_github
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines.pipes import write_data_to_yaml_file

from minecode_pipelines.pipes import get_checkpoint_from_file
from scanpipe.pipes.federatedcode import clone_repository

from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from minecode_pipelines.utils import cycle_from_index

PACKAGE_BATCH_SIZE = 100
SWIFT_CHECKPOINT_PATH = "swift/checkpoints.json"

MINECODE_DATA_SWIFT_REPO = os.environ.get(
    "MINECODE_DATA_SWIFT_REPO", "https://github.com/aboutcode-data/minecode-data-swift-test"
)
MINECODE_SWIFT_INDEX_REPO = "https://github.com/SwiftPackageIndex/"


def store_swift_packages(package_repo_url, tags_and_commits, cloned_data_repo):
    """Collect Swift package versions into purls and write them to the repo."""
    org, name = split_org_repo(package_repo_url)
    org = "github.com/" + org
    purl = PackageURL(type="swift", namespace=org, name=name)
    base_purl = get_core_purl(purl)

    updated_purls = []
    for tag, _ in tags_and_commits:
        purl = PackageURL(type="swift", namespace=org, name=name, version=tag).to_string()
        updated_purls.append(purl)

    purl_yaml_path = cloned_data_repo.working_dir / hashid.get_package_purls_yml_file_path(
        base_purl
    )
    write_data_to_yaml_file(path=purl_yaml_path, data=updated_purls)
    return purl_yaml_path, base_purl


def mine_and_publish_swift_packageurls(logger):
    """
    Clone Swift-related repositories, process Swift packages, and publish their
    Package URLs (purls) to the data repository.

    This function:
      1. Clones the Swift index, data, and pipelines config repositories.
      2. Loads the list of Swift package repositories from `packages.json`.
      3. Iterates over each package, fetching tags/commits and generating purls.
      4. Commits and pushes purl files to the data repository in batches.
      5. Updates checkpoint information in the config repository to track progress.

    logger (callable): Optional logging function for status updates.
    Returns: list: A list of cloned repository objects in the order:
    [swift_index_repo, cloned_data_repo, cloned_config_repo]
    """

    swift_index_repo = clone_repository(MINECODE_SWIFT_INDEX_REPO)
    cloned_data_repo = clone_repository(MINECODE_DATA_SWIFT_REPO)
    cloned_config_repo = clone_repository(MINECODE_PIPELINES_CONFIG_REPO)

    if logger:
        logger(f"{MINECODE_SWIFT_INDEX_REPO} repo cloned at: {swift_index_repo.working_dir}")
        logger(f"{MINECODE_DATA_SWIFT_REPO} repo cloned at: {cloned_data_repo.working_dir}")
        logger(f"{MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {cloned_config_repo.working_dir}")

    packages_path = Path(swift_index_repo.working_dir) / "packages.json"
    with open(packages_path) as f:
        packages_urls = json.load(f)

    counter = 0
    purl_files = []
    purls = []

    swift_checkpoint = get_checkpoint_from_file(
        cloned_repo=cloned_config_repo, path=SWIFT_CHECKPOINT_PATH
    )

    start_index = swift_checkpoint.get("start_index", 0)

    if logger:
        logger(f"Processing total files: {len(packages_urls)}")

    for idx, package_repo_url in enumerate(cycle_from_index(packages_urls, start_index)):
        git_ls_remote = fetch_git_tags_raw(package_repo_url, 60, logger)
        if not git_ls_remote:
            continue

        tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)
        if not tags_and_commits:
            continue

        purl_file, base_purl = store_swift_packages(
            package_repo_url, tags_and_commits, cloned_data_repo
        )

        logger(f"writing packageURLs for package: {str(base_purl)} at: {purl_file}")
        purl_files.append(purl_file)
        purls.append(str(base_purl))
        counter += 1

        if counter >= PACKAGE_BATCH_SIZE:
            commit_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                purls=purls,
                mine_type="packageURL",
                tool_name="pkg:pypi/minecode-pipelines",
                tool_version=VERSION,
            )

            push_changes(repo=cloned_data_repo)
            purl_files = []
            purls = []
            counter = 0

            if start_index == idx:
                continue

            settings_data = {
                "date": str(datetime.now()),
                "start_index": idx,
            }

            update_checkpoints_in_github(
                checkpoint=settings_data,
                cloned_repo=cloned_config_repo,
                path=SWIFT_CHECKPOINT_PATH,
            )

    commit_changes(
        repo=cloned_data_repo,
        files_to_commit=purl_files,
        purls=purls,
        mine_type="packageURL",
        tool_name="pkg:pypi/minecode-pipelines",
        tool_version=VERSION,
    )

    push_changes(repo=cloned_data_repo)
    return [swift_index_repo, cloned_data_repo, cloned_config_repo]
