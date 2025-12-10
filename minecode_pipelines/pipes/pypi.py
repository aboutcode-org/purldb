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
from minecode_pipelines.utils import get_temp_dir

from scanpipe.pipes.federatedcode import delete_local_clone
from packageurl import PackageURL
from scanpipe.pipes.federatedcode import clone_repository

# If True, show full details on fetching packageURL for
# a package name present in the index
LOG_PACKAGEURL_DETAILS = False


PACKAGE_FILE_NAME = "PypiPackages.json"
PYPI_SIMPLE_CHECKPOINT_PATH = "pypi/simple_index/" + PACKAGE_FILE_NAME
PYPI_CHECKPOINT_PATH = "pypi/checkpoints.json"
PYPI_PACKAGES_CHECKPOINT_PATH = "pypi/packages_checkpoint.json"


# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_PYPI_REPO = "https://github.com/aboutcode-data/minecode-data-pypi-test"


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

    config_repo = clone_repository(
        repo_url=MINECODE_PIPELINES_CONFIG_REPO,
        clone_path=get_temp_dir(),
        logger=logger,
    )

    if state == INITIAL_SYNC_STATE:
        if logger:
            logger("Getting packages from pypi checkpoint")
        packages_file = get_packages_file_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=PYPI_SIMPLE_CHECKPOINT_PATH,
            name=PACKAGE_FILE_NAME,
        )
        return packages_file, state, config_repo

    if logger:
        logger("Getting packages from pypi simple index")

    packages = get_pypi_packages(pypi_repo=PYPI_REPO, logger=logger)
    packages_file = write_packages_json(packages=packages, name=PACKAGE_FILE_NAME)

    if not state:
        if logger:
            logger("Checkpointing packages from pypi simple index")
        update_checkpoints_in_github(
            checkpoint=packages,
            cloned_repo=config_repo,
            path=PYPI_SIMPLE_CHECKPOINT_PATH,
            logger=logger,
        )
        if logger:
            logger(f"Updating checkpoint mining state to: {INITIAL_SYNC_STATE}")
        update_checkpoint_state(
            cloned_repo=config_repo,
            state=INITIAL_SYNC_STATE,
            logger=logger,
        )

    return packages_file, state, config_repo


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
    logger=None,
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
        logger=logger,
    )


def update_pypi_checkpoints(
    last_serial,
    state,
    cloned_repo,
    checkpoint_path=PYPI_CHECKPOINT_PATH,
    logger=None,
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
        logger=logger,
    )


def get_packages_file_from_checkpoint(config_repo, checkpoint_path, name):
    packages = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    return write_packages_json(packages, name=name)


def get_pypi_packages_to_sync(packages_file, state, logger=None):
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
        return packages, last_serial

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
            return [], last_serial

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

    return packages_to_sync, last_serial


def mine_and_publish_pypi_packageurls(packages_to_sync, packages_mined, logger=None):

    for package in packages_to_sync:
        if not package:
            continue

        # fetch packageURLs for package
        name = package.get("name")
        if logger and LOG_PACKAGEURL_DETAILS:
            logger(f"getting packageURLs for package: {name}")

        # get repo and path for package
        base_purl = PackageURL(type=PYPI_TYPE, name=name).to_string()
        packageurls = get_pypi_packageurls(name)
        if not packageurls:
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"Package versions not present for package: {name}")

            # We don't want to try fetching versions for these again
            packages_mined.append(base_purl)
            continue

        if logger and LOG_PACKAGEURL_DETAILS:
            logger(f"getting packageURLs for package: {base_purl}:")
            purls_string = " ".join(packageurls)
            logger(f"packageURLs: {purls_string}")

        yield base_purl, packageurls


def save_mined_packages_in_checkpoint(packages_mined, config_repo, logger=None):
    """Update mined packages checkpoint after processing a batch of packages."""
    if logger:
        logger(f"Checkpointing processed packages to: {PYPI_PACKAGES_CHECKPOINT_PATH}")

    update_mined_packages_in_checkpoint(
        packages=packages_mined,
        cloned_repo=config_repo,
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        checkpoint_path=PYPI_PACKAGES_CHECKPOINT_PATH,
        logger=logger,
    )


def update_state_and_checkpoints(config_repo, last_serial, logger=None):
    # If we are finshed mining all the packages in the intial sync, we can now
    # periodically sync the packages from latest
    if state == INITIAL_SYNC_STATE:
        if logger:
            logger(f"{INITIAL_SYNC_STATE} completed. starting: {PERIODIC_SYNC_STATE}")

        state = PERIODIC_SYNC_STATE
        update_checkpoint_state(
            cloned_repo=config_repo,
            state=state,
            logger=logger,
        )
        # refresh packages checkpoint once to only checkpoint new packages
        update_checkpoints_in_github(
            checkpoint={"packages_mined": []},
            cloned_repo=config_repo,
            path=PYPI_PACKAGES_CHECKPOINT_PATH,
            logger=logger,
        )

    # update last_serial to minecode checkpoints whenever we finish mining
    # either from checkpoints or from the latest pypi
    if logger:
        logger(f"Updating checkpoint at: {PYPI_CHECKPOINT_PATH} with last serial: {last_serial}")
    update_pypi_checkpoints(
        last_serial=last_serial,
        state=state,
        cloned_repo=config_repo,
        logger=logger,
    )

    if logger:
        logger(f"Deleting local clone at: {config_repo.working_dir}")
    delete_local_clone(config_repo)
