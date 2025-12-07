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

from minecode_pipelines.miners.composer import get_composer_packages
from minecode_pipelines.miners.composer import load_composer_packages
from minecode_pipelines.miners.composer import get_composer_purl

from minecode_pipelines.utils import cycle_from_index, grouper

PACKAGE_BATCH_SIZE = 100


def mine_composer_packages():
    """Mine Composer package names from Packagist and return List of (vendor, package) tuples."""
    packages_file = get_composer_packages()
    return load_composer_packages(packages_file)


def mine_composer_packageurls(packages, start_index):
    """Mine Composer packages from Packagist"""
    packages_iter = cycle_from_index(packages, start_index)
    for batch_index, package_batch in enumerate(
        grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_iter)
    ):
        for item in package_batch:
            if not item:
                continue

            vendor, package = item
            yield get_composer_purl(vendor=vendor, package=package)
