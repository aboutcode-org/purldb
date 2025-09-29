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

from minecode_pipelines import VERSION
from minecode_pipelines.pipes import write_packageurls_to_file
from minecode_pipelines.pipes import fetch_checkpoint_from_github
from minecode_pipelines.pipes import update_checkpoints_in_github
from minecode_pipelines.pipes import get_mined_packages_from_checkpoint
from minecode_pipelines.pipes import update_mined_packages_in_checkpoint
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines.pipes import INITIAL_SYNC_STATE
from minecode_pipelines.pipes import PERIODIC_SYNC_STATE


from minecode_pipelines.miners.pypi import get_pypi_packages
from minecode_pipelines.miners.pypi import get_pypi_packageurls
from minecode_pipelines.miners.pypi import load_pypi_packages
from minecode_pipelines.miners.pypi import PYPI_REPO
from minecode_pipelines.miners.pypi import write_packages_json

from minecode_pipelines.miners.pypi import PYPI_TYPE
from minecode_pipelines.utils import grouper

from aboutcode.hashid import get_package_base_dir
from packageurl import PackageURL
from scanpipe.pipes.federatedcode import clone_repository

from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes


# If True, show full details on fetching packageURL for
# a package name present in the index
LOG_PACKAGEURL_DETAILS = False


PACKAGE_FILE_NAME = "PypiPackages.json"
PYPI_SIMPLE_CHECKPOINT_PATH = "pypi/simple_index/" + PACKAGE_FILE_NAME
PYPI_CHECKPOINT_PATH = "pypi/checkpoints.json"
PYPI_PACKAGES_CHECKPOINT_PATH = "pypi/packages_checkpoint.json"


# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_PYPI_REPO = "https://github.com/aboutcode-data/minecode-data-pypi-test"


# Number of packages
PACKAGE_BATCH_SIZE = 1000


def mine_pypi_packages(logger=None):
    """
    Mine pypi package names from pypi simple and save to checkpoints,
    or get packages from saved checkpoints. We have 3 cases:
    1. periodic sync: we get latest packages newly released in pypi, for a period
    2. intial sync: we get packages from checkpoint which we're trying to sync upto
    3. first sync: we get latest packages from pypi and save to checkpoints
    """

    pypi_checkpoints = fetch_checkpoint_from_github(
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        checkpoint_path=PYPI_CHECKPOINT_PATH,
    )
    state = pypi_checkpoints.get("state")
    if logger:
        logger(f"Mining state from checkpoint: {state}")

    cloned_repo = clone_repository(repo_url=MINECODE_PIPELINES_CONFIG_REPO)

    if state == INITIAL_SYNC_STATE:
        if logger:
            logger("Getting packages from pypi checkpoint")
        packages_file = get_packages_file_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=PYPI_SIMPLE_CHECKPOINT_PATH,
            name=PACKAGE_FILE_NAME,
        )
        return packages_file, state

    if logger:
        logger("Getting packages from pypi simple index")

    packages = get_pypi_packages(pypi_repo=PYPI_REPO, logger=logger)
    packages_file = write_packages_json(packages=packages, name=PACKAGE_FILE_NAME)

    if not state:
        if logger:
            logger("Checkpointing packages from pypi simple index")
        update_checkpoints_in_github(
            checkpoint=packages,
            cloned_repo=cloned_repo,
            path=PYPI_SIMPLE_CHECKPOINT_PATH,
        )
        if logger:
            logger(f"Updating checkpoint mining state to: {INITIAL_SYNC_STATE}")
        update_checkpoint_state(cloned_repo=cloned_repo, state=INITIAL_SYNC_STATE)

    return packages_file, state


def fetch_last_serial_mined(config_repo, settings_path):
    """
    Fetch "last_serial" for the last mined packages.

    This is a simple JSON in a github repo containing mining checkpoints
    with the "last_serial" from the pypi index which was mined. Example:
    https://github.com/aboutcode-data/minecode-pipelines-config/blob/main/pypi/checkpoints.json
    """
    checkpoints = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=settings_path,
    )
    return checkpoints.get("last_serial")


def update_checkpoint_state(
    cloned_repo,
    state,
    config_repo=MINECODE_PIPELINES_CONFIG_REPO,
    checkpoint_path=PYPI_CHECKPOINT_PATH,
):
    checkpoint = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    checkpoint["state"] = state
    checkpoint["last_updated"] = str(datetime.now())
    update_checkpoints_in_github(
        checkpoint=checkpoint,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
    )


def update_pypi_checkpoints(
    last_serial,
    state,
    cloned_repo,
    checkpoint_path=PYPI_CHECKPOINT_PATH,
):
    checkpoint = {
        "last_updated": str(datetime.now()),
        "state": state,
        "last_serial": last_serial,
    }
    update_checkpoints_in_github(
        checkpoint=checkpoint,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
    )


def get_packages_file_from_checkpoint(config_repo, checkpoint_path, name):
    packages = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    return write_packages_json(packages, name=name)


def mine_and_publish_pypi_packageurls(packages_file, state, logger=None):
    last_serial_fetched = fetch_last_serial_mined(
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        settings_path=PYPI_CHECKPOINT_PATH,
    )
    if logger:
        logger(f"Last serial number mined: {last_serial_fetched}")
        logger(f"Mining state: {state}")

    # this is either from pypi or from checkpoints
    last_serial, packages = load_pypi_packages(packages_file)
    if logger:
        logger(f"Last serial number fetched from index/checkpoint: {last_serial}")
        logger(f"# of package names fetched from index/checkpoint: {len(packages)}")

    if not packages:
        return

    synced_packages = get_mined_packages_from_checkpoint(
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        checkpoint_path=PYPI_PACKAGES_CHECKPOINT_PATH,
    )
    if not state:
        if logger:
            logger("Initializing package mining:")
        packages_to_sync = packages

    elif state == PERIODIC_SYNC_STATE:
        # We are all synced up from the index
        if last_serial == last_serial_fetched:
            return

        packages_to_sync = [
            package
            for package in packages
            if last_serial_fetched < package.get("_last-serial")
            and package.get("name") not in synced_packages
        ]
        if logger:
            logger(
                f"Starting periodic package mining for {len(packages_to_sync)} packages, "
                f"which has been released after serial: {last_serial_fetched}"
            )

    elif state == INITIAL_SYNC_STATE:
        packages_to_sync = [
            package for package in packages if package.get("name") not in synced_packages
        ]
        if logger:
            logger(
                f"Starting initial package mining for {len(packages_to_sync)} packages from checkpoint"
            )

    # clone repo
    cloned_data_repo = clone_repository(repo_url=MINECODE_DATA_PYPI_REPO)
    cloned_config_repo = clone_repository(repo_url=MINECODE_PIPELINES_CONFIG_REPO)
    if logger:
        logger(f"{MINECODE_DATA_PYPI_REPO} repo cloned at: {cloned_data_repo.working_dir}")
        logger(f"{MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {cloned_config_repo.working_dir}")

    for package_batch in grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_to_sync):
        packages_mined = []
        purls = []
        purl_files = []

        if logger and LOG_PACKAGEURL_DETAILS:
            logger("Starting package mining for a batch of packages")

        for package in package_batch:
            if not package:
                continue

            # fetch packageURLs for package
            name = package.get("name")
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"getting packageURLs for package: {name}")

            packageurls = get_pypi_packageurls(name)
            if not packageurls:
                if logger and LOG_PACKAGEURL_DETAILS:
                    logger(f"Package versions not present for package: {name}")

                # We don't want to try fetching versions for these again
                packages_mined.append(name)
                continue

            # get repo and path for package
            base_purl = PackageURL(type=PYPI_TYPE, name=name).to_string()
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

            packages_mined.append(name)

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
            tool_name="pkg:pypi/minecode-pipelines",
            tool_version=VERSION,
        )

        # Push changes to remote repository
        push_changes(repo=cloned_data_repo)

        # we need to update mined packages checkpoint for every batch
        if logger:
            logger(f"Checkpointing processed packages to: {PYPI_PACKAGES_CHECKPOINT_PATH}")

        update_mined_packages_in_checkpoint(
            packages=packages_mined,
            cloned_repo=cloned_config_repo,
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=PYPI_PACKAGES_CHECKPOINT_PATH,
        )

    # If we are finshed mining all the packages in the intial sync, we can now
    # periodically sync the packages from latest
    if state == INITIAL_SYNC_STATE:
        if logger:
            logger(f"{INITIAL_SYNC_STATE} completed. starting: {PERIODIC_SYNC_STATE}")

        state = PERIODIC_SYNC_STATE
        update_checkpoint_state(
            cloned_repo=cloned_config_repo,
            state=state,
        )
        # refresh packages checkpoint once to only checkpoint new packages
        update_checkpoints_in_github(
            checkpoint={"packages_mined": []},
            cloned_repo=cloned_config_repo,
            path=PYPI_PACKAGES_CHECKPOINT_PATH,
        )

    # update last_serial to minecode checkpoints whenever we finish mining
    # either from checkpoints or from the latest pypi
    if logger:
        logger(f"Updating checkpoint at: {PYPI_CHECKPOINT_PATH} with last serial: {last_serial}")
    update_pypi_checkpoints(last_serial=last_serial, state=state, cloned_repo=cloned_config_repo)

    repos_to_clean = [cloned_data_repo, cloned_config_repo]
    return repos_to_clean
