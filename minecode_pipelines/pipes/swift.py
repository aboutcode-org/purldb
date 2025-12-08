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

from minecode_pipelines.miners.swift import fetch_git_tags_raw
from minecode_pipelines.miners.swift import get_tags_and_commits_from_git_output
from minecode_pipelines.miners.swift import split_org_repo
from minecode_pipelines.utils import cycle_from_index, grouper

PACKAGE_BATCH_SIZE = 100


def mine_swift_packageurls(packages_urls, start_index, logger):
    """Mine Swift PackageURLs from package index."""

    packages_iter = cycle_from_index(packages_urls, start_index)
    for batch_index, package_batch in enumerate(
        grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_iter)
    ):
        for item in package_batch:
            if not item:
                continue
        package_repo_url = item
        git_ls_remote = fetch_git_tags_raw(package_repo_url, 60, logger)
        if not git_ls_remote:
            continue

        tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)
        if not tags_and_commits:
            continue

        yield generate_package_urls(
            package_repo_url=package_repo_url, tags_and_commits=tags_and_commits
        )


def load_swift_package_urls(swift_index_repo):
    packages_path = Path(swift_index_repo.working_dir) / "packages.json"
    with open(packages_path) as f:
        packages_urls = json.load(f)
    return packages_urls


def generate_package_urls(package_repo_url, tags_and_commits):
    org, name = split_org_repo(package_repo_url)
    org = "github.com/" + org
    base_purl = PackageURL(type="swift", namespace=org, name=name)
    updated_purls = []

    for tag, commit in tags_and_commits:
        purl = None
        if tag == "HEAD":
            if len(tags_and_commits) == 1:
                purl = PackageURL(
                    type="swift", namespace=org, name=name, version=commit
                ).to_string()
        else:
            purl = PackageURL(type="swift", namespace=org, name=name, version=tag).to_string()

        if purl:
            updated_purls.append(purl)

    return base_purl, updated_purls
