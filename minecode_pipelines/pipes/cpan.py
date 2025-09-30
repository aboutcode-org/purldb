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

from minecode_pipelines import VERSION
from minecode_pipelines.pipes import write_packageurls_to_file

from minecode_pipelines.miners.cpan import get_cpan_packages
from minecode_pipelines.miners.cpan import get_cpan_packageurls
from minecode_pipelines.miners.cpan import CPAN_REPO

from minecode_pipelines.miners.cpan import CPAN_TYPE
from minecode_pipelines.utils import grouper

from aboutcode.hashid import get_package_base_dir
from packageurl import PackageURL
from scanpipe.pipes.federatedcode import clone_repository

from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes


# If True, show full details on fetching packageURL for
# a package name present in the index
LOG_PACKAGEURL_DETAILS = False

PACKAGE_BATCH_SIZE = 500


# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_CPAN_REPO = "https://github.com/aboutcode-data/minecode-data-cpan-test"


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

    # clone repo
    cloned_data_repo = clone_repository(repo_url=MINECODE_DATA_CPAN_REPO)
    if logger:
        logger(f"{MINECODE_DATA_CPAN_REPO} repo cloned at: {cloned_data_repo.working_dir}")

    for package_batch in grouper(n=PACKAGE_BATCH_SIZE, iterable=package_path_by_name.keys()):
        packages_mined = []
        purls = []
        purl_files = []

        if logger and LOG_PACKAGEURL_DETAILS:
            logger("Starting package mining for a batch of packages")

        for package_name in package_batch:
            if not package_name:
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
            package_base_dir = get_package_base_dir(purl=base_purl)

            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"writing packageURLs for package: {base_purl} at: {package_base_dir}")
                purls_string = " ".join(packageurls)
                logger(f"packageURLs: {purls_string}")

            # write packageURLs to file
            purl_file = write_packageurls_to_file(
                repo=cloned_data_repo,
                base_dir=package_base_dir,
                packageurls=packageurls,
            )
            purl_files.append(purl_file)
            purls.append(base_purl)

            packages_mined.append(package_name)

        if logger:
            purls_string = " ".join(purls)
            logger("Committing and pushing changes for a batch of packages: ")
            logger(f"{purls_string}")

        # commit changes
        commit_changes(
            repo=cloned_data_repo,
            files_to_commit=purl_files,
            purls=purls,
            mine_type="packageURL",
            tool_name="pkg:cpan/minecode-pipelines",
            tool_version=VERSION,
        )

        # Push changes to remote repository
        push_changes(repo=cloned_data_repo)

    repos_to_clean = [cloned_data_repo]
    return repos_to_clean
