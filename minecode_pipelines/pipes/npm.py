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
from minecode_pipelines.pipes import update_checkpoints_file_in_github
from minecode_pipelines.pipes import get_mined_packages_from_checkpoint
from minecode_pipelines.pipes import update_mined_packages_in_checkpoint
from minecode_pipelines.pipes import get_packages_file_from_checkpoint
from minecode_pipelines.pipes import update_checkpoint_state
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines.pipes import INITIAL_SYNC_STATE
from minecode_pipelines.pipes import PERIODIC_SYNC_STATE
from minecode_pipelines.pipes import write_packages_json
from minecode_pipelines.pipes import compress_packages_file
from minecode_pipelines.pipes import decompress_packages_file


from minecode_pipelines.miners.npm import get_npm_packages
from minecode_pipelines.miners.npm import get_updated_npm_packages
from minecode_pipelines.miners.npm import get_current_last_seq
from minecode_pipelines.miners.npm import load_npm_packages
from minecode_pipelines.miners.npm import get_npm_packageurls
from minecode_pipelines.miners.npm import NPM_REPLICATE_REPO

from minecode_pipelines.miners.npm import NPM_TYPE
from minecode_pipelines.utils import grouper

from packageurl import PackageURL

from aboutcode.hashid import get_package_base_dir


from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes


PACKAGE_FILE_NAME = "NPMPackages.json"
COMPRESSED_PACKAGE_FILE_NAME = "NPMPackages.json.gz"
NPM_REPLICATE_CHECKPOINT_PATH = "npm/" + PACKAGE_FILE_NAME
COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH = "npm/" + COMPRESSED_PACKAGE_FILE_NAME
NPM_CHECKPOINT_PATH = "npm/checkpoints.json"
NPM_PACKAGES_CHECKPOINT_PATH = "npm/packages_checkpoint.json"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_NPM_REPO = "https://github.com/aboutcode-data/minecode-data-npm-test"


PACKAGE_BATCH_SIZE = 1000


def mine_npm_packages(logger=None):
    """
    Mine npm package names from npm replicate index and save to checkpoints,
    or get packages from saved checkpoints. We have 3 cases:

    1. first sync: we get latest set of packages from the "_all_docs" API endpoint
       of npm replicate and save this and last sequence of the package to checkpoints.
    2. intial sync: we get packages from checkpoint which we're trying to sync upto
    3. periodic sync: we get latest packages newly released in npm through the
       "_changes" API, for a period, from our last mined sequence of package.
    """

    npm_checkpoints = fetch_checkpoint_from_github(
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        checkpoint_path=NPM_CHECKPOINT_PATH,
    )
    state = npm_checkpoints.get("state")
    if logger:
        logger(f"Mining state from checkpoint: {state}")

    cloned_repo = clone_repository(repo_url=MINECODE_PIPELINES_CONFIG_REPO)

    # This is the first time we are syncing from npm replicate
    if not state:
        last_seq = get_current_last_seq(replicate_url=NPM_REPLICATE_REPO)
        if logger:
            logger(
                f"Starting initial checkpointing of packages from npm replicate till seq: {last_seq}"
            )

        packages = get_npm_packages(replicate_url=NPM_REPLICATE_REPO)
        packages_file = write_packages_json(
            packages=packages,
            name=PACKAGE_FILE_NAME,
        )
        compressed_packages_file = packages_file + ".gz"
        compress_packages_file(
            packages_file=packages_file,
            compressed_packages_file=compressed_packages_file,
        )
        update_checkpoints_file_in_github(
            checkpoints_file=compressed_packages_file,
            cloned_repo=cloned_repo,
            path=COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH,
        )

        if logger:
            logger(f"Updating checkpoint mining state to: {INITIAL_SYNC_STATE}")
            logger(f"Updating checkpoint mining last_seq to: {last_seq}")

        update_npm_checkpoints(
            cloned_repo=cloned_repo,
            state=INITIAL_SYNC_STATE,
            last_seq=last_seq,
            checkpoint_path=NPM_CHECKPOINT_PATH,
        )

    elif state == INITIAL_SYNC_STATE:
        if logger:
            logger("Getting packages to sync from npm checkpoint")

        last_seq = fetch_last_seq_mined(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            settings_path=NPM_CHECKPOINT_PATH,
        )

        compressed_packages_file = get_packages_file_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH,
            name=COMPRESSED_PACKAGE_FILE_NAME,
        )
        packages_file = compressed_packages_file.replace(".gz", "")
        decompress_packages_file(
            packages_file=packages_file,
            compressed_packages_file=compressed_packages_file,
        )

    elif state == PERIODIC_SYNC_STATE:
        last_seq = fetch_last_seq_mined(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            settings_path=NPM_CHECKPOINT_PATH,
        )
        if logger:
            logger(
                f"Getting latest packages from npm replicate index changes after seq: {last_seq}"
            )

        packages, last_seq = get_updated_npm_packages(
            last_seq=last_seq,
            replicate_url=NPM_REPLICATE_REPO,
        )
        packages_file = write_packages_json(
            packages=packages,
            name=PACKAGE_FILE_NAME,
        )

    return packages_file, state, last_seq


def update_npm_checkpoints(
    cloned_repo,
    checkpoint_path,
    state=None,
    last_seq=None,
    config_repo=MINECODE_PIPELINES_CONFIG_REPO,
):
    checkpoint = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    if state:
        checkpoint["state"] = state
    if last_seq:
        checkpoint["last_seq"] = last_seq

    checkpoint["date"] = str(datetime.now())
    update_checkpoints_in_github(
        checkpoint=checkpoint,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
    )


def fetch_last_seq_mined(config_repo, settings_path):
    """
    Fetch "last_seq" for the last mined packages.

    This is a simple JSON in a github repo containing mining checkpoints
    with the "last_seq" from the npm replicate index which was mined. Example:
    https://github.com/aboutcode-data/minecode-pipelines-config/blob/main/npm/checkpoints.json
    """
    checkpoints = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=settings_path,
    )
    return checkpoints.get("last_seq")


def mine_and_publish_npm_packageurls(packages_file, state, last_seq, logger=None):
    if logger:
        logger(f"Last serial number mined: {last_seq}")
        logger(f"Mining state: {state}")

    # this is either from npm replicate or from checkpoints
    packages = load_npm_packages(packages_file)
    if logger:
        logger(f"# of package names fetched from index/checkpoint: {len(packages)}")

    if not packages:
        return

    if not state:
        packages_to_sync = packages
        if logger:
            logger(f"Starting package mining for {len(packages_to_sync)} packages")

    elif state == INITIAL_SYNC_STATE or state == PERIODIC_SYNC_STATE:
        synced_packages = get_mined_packages_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=NPM_PACKAGES_CHECKPOINT_PATH,
        )
        packages_to_sync = [package for package in packages if package not in synced_packages]
        if logger:
            logger(
                f"Starting initial package mining for {len(packages_to_sync)} packages from checkpoint"
            )

    # clone repo
    cloned_data_repo = clone_repository(repo_url=MINECODE_DATA_NPM_REPO)
    cloned_config_repo = clone_repository(repo_url=MINECODE_PIPELINES_CONFIG_REPO)
    if logger:
        logger(f"{MINECODE_DATA_NPM_REPO} repo cloned at: {cloned_data_repo.working_dir}")
        logger(f"{MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {cloned_config_repo.working_dir}")

    for package_batch in grouper(n=PACKAGE_BATCH_SIZE, iterable=packages_to_sync):
        packages_mined = []
        purls = []
        purl_files = []

        if logger:
            logger("Starting package mining for a batch of packages")

        for package_name in package_batch:
            if not package_name:
                continue

            # fetch packageURLs for package
            if logger:
                logger(f"getting packageURLs for package: {package_name}")

            packageurls = get_npm_packageurls(package_name)
            if not packageurls:
                if logger:
                    logger(f"Could not fetch package versions for package: {package_name}")
                continue

            # get repo and path for package
            base_purl = PackageURL(type=NPM_TYPE, name=package_name).to_string()
            package_base_dir = get_package_base_dir(purl=base_purl)

            if logger:
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
            tool_name="pkg:pypi/minecode-pipelines",
            tool_version=VERSION,
        )

        # Push changes to remote repository
        push_changes(repo=cloned_data_repo)

        # As we are mining the packages to sync with the index,
        # we need to update mined packages checkpoint for every batch
        # so we can continue mining the other packages after restarting
        if logger:
            logger("Checkpointing processed packages to: {NPM_PACKAGES_CHECKPOINT_PATH}")

        packages_checkpoint = packages_mined + synced_packages
        update_mined_packages_in_checkpoint(
            packages=packages_checkpoint,
            cloned_repo=cloned_config_repo,
            checkpoint_path=NPM_PACKAGES_CHECKPOINT_PATH,
        )

    # If we are finished mining all the packages in the intial sync, we can now
    # periodically sync the packages from latest
    if state == INITIAL_SYNC_STATE:
        if logger:
            logger(f"{INITIAL_SYNC_STATE} completed. starting: {PERIODIC_SYNC_STATE}")
        update_checkpoint_state(
            cloned_repo=cloned_config_repo,
            state=PERIODIC_SYNC_STATE,
        )

    # If we are finished mining all the packages in the periodic sync, we can now update
    # the last sequence updated
    if state == PERIODIC_SYNC_STATE:
        if logger:
            logger(f"{PERIODIC_SYNC_STATE} completed. Updating last seq to: {last_seq}")

        update_npm_checkpoints(
            cloned_repo=cloned_config_repo,
            checkpoint_path=NPM_CHECKPOINT_PATH,
            state=PERIODIC_SYNC_STATE,
            last_seq=last_seq,
        )

    # Refresh mined packages checkpoint
    update_checkpoints_in_github(
        checkpoint={"packages_mined": []},
        cloned_repo=cloned_config_repo,
        path=NPM_PACKAGES_CHECKPOINT_PATH,
    )

    repos_to_clean = [cloned_data_repo, cloned_config_repo]
    return repos_to_clean
