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

from minecode_pipelines.miners.cpan import get_cpan_packages
from minecode_pipelines.miners.cpan import get_cpan_packageurls
from minecode_pipelines.miners.cpan import CPAN_REPO

from minecode_pipelines.miners.cpan import CPAN_TYPE
from minecode_pipelines.utils import grouper

from aboutcode.hashid import get_package_base_dir
from packageurl import PackageURL

# If True, show full details on fetching packageURL for
# a package name present in the index
LOG_PACKAGEURL_DETAILS = False

PACKAGE_BATCH_SIZE = 500


def mine_cpan_packages(logger=None):
    if logger:
        logger("Getting packages from cpan index")

    package_path_by_name = get_cpan_packages(cpan_repo=CPAN_REPO, logger=logger)

    if logger:
        packages_count = len(package_path_by_name.keys())
        logger(f"Mined {packages_count} packages from cpan index")

    return package_path_by_name


def mine_and_publish_cpan_packageurls(package_path_by_name, logger=None):
    if not package_path_by_name:
        return

    packageurls_by_base_purl = {}
    for package_batch in grouper(n=PACKAGE_BATCH_SIZE, iterable=package_path_by_name.keys()):
        packages_mined = []

        if logger and LOG_PACKAGEURL_DETAILS:
            logger("Starting package mining for a batch of packages")

        for package_name in package_batch:
            if not package_name or package_name in packages_mined:
                continue

            # fetch packageURLs for package
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"getting packageURLs for package: {package_name}")

            path_prefix = package_path_by_name.get(package_name)
            if not path_prefix:
                continue

            packageurls = get_cpan_packageurls(
                name=package_name,
                path_prefix=path_prefix,
                logger=logger,
            )
            if not packageurls:
                if logger and LOG_PACKAGEURL_DETAILS:
                    logger(f"Package versions not present for package: {package_name}")

                # We don't want to try fetching versions for these again
                packages_mined.append(package_name)
                continue

            # get repo and path for package
            base_purl = PackageURL(type=CPAN_TYPE, name=package_name).to_string()
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"fetched packageURLs for package: {base_purl}")
                purls_string = " ".join(packageurls)
                logger(f"packageURLs: {purls_string}")

            packages_mined.append(package_name)
            packageurls_by_base_purl[base_purl] = packageurls
    
    return packageurls_by_base_purl
