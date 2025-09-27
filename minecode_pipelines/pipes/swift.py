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
from aboutcode import hashid
from aboutcode.hashid import get_core_purl
from packageurl import PackageURL
from minecode.miners.github import split_org_repo
from minecode_pipelines.miners.swift import fetch_tags_raw
from minecode_pipelines.pipes import write_packageurls_to_file
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from purl2vcs.find_source_repo import get_tags_and_commits_from_git_output

PACKAGE_BATCH_SIZE = 100


def store_swift_packages(package_repo_url, tags_and_commits, repo):
    """Collect Swift package versions into purls and write them to the repo."""
    org, name = split_org_repo(package_repo_url)
    org = "github.com/" + org
    purl = PackageURL(type="swift", namespace=org, name=name)
    base_purl = get_core_purl(purl)

    updated_purls = []
    for tag, _ in tags_and_commits:
        purl = PackageURL(type="swift", namespace=org, name=name, version=tag).to_string()
        updated_purls.append(purl)

    ppath = hashid.get_package_purls_yml_file_path(base_purl)
    return write_packageurls_to_file(repo, ppath, updated_purls), base_purl


def process_swift_packages(swift_index_repo, cloned_data_repo, logger):
    """Process swift packages and write them to the repo."""
    packages_path = Path(swift_index_repo.working_dir) / "packages.json"
    with open(packages_path) as f:
        packages_urls = json.load(f)

    counter = 0
    purl_files = []
    purls = []
    total_files = len(packages_urls)

    logger(f"Processing total files: {total_files}")
    for idx, package_repo_url in enumerate(packages_urls):
        git_ls_remote = fetch_tags_raw(package_repo_url)
        tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)
        purl_file, base_purl = store_swift_packages(
            package_repo_url, tags_and_commits, cloned_data_repo
        )
        purl_files.append(purl_file)
        purls.append(str(base_purl))
        counter += 1

        if counter >= PACKAGE_BATCH_SIZE & idx == total_files:
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
