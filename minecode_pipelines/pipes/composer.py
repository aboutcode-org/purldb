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

from aboutcode.hashid import get_package_base_dir
from minecode_pipelines.miners import write_packageurls_to_file
from minecode_pipelines.miners.composer import get_composer_packages
from minecode_pipelines.miners.composer import load_composer_packages
from minecode_pipelines.miners.composer import get_composer_purl
from minecode_pipelines.pipes import commit_and_push_changes
from minecode_pipelines.pipes import git_stage_purls


def mine_composer_packages(logger=None):
    """Mine Composer package names from Packagist and return List of (vendor, package) tuples."""
    packages_file = get_composer_packages()
    return load_composer_packages(packages_file)


def mine_and_publish_composer_purls(packages, fed_repo, logger=None):
    """Mine Composer packages and publish their PURLs to a FederatedCode repository."""

    counter = 0
    for vendor, package in packages:
        if logger:
            logger(f"getting packageURLs for package: {vendor}/{package}")

        purls = get_composer_purl(vendor, package)
        if not purls:
            continue

        base_purl = purls[0]
        package_base_dir = get_package_base_dir(purl=base_purl)

        if logger:
            logger(f"writing packageURLs for package: {base_purl} at: {package_base_dir}")
            purls_string = " ".join(purls)
            logger(f"packageURLs: {purls_string}")

        purl_file = write_packageurls_to_file(
            repo=fed_repo,
            base_dir=package_base_dir,
            packageurls=purls,
        )
        git_stage_purls(repo=fed_repo, purls_file=purl_file, purls=purls)

        counter += 1
        if counter == 1000:
            commit_and_push_changes(repo=fed_repo)
            counter = 0

    commit_and_push_changes(repo=fed_repo)
