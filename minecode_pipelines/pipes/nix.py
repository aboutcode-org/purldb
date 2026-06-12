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
from minecode_pipelines.pipes import update_checkpoints_file_in_github
from minecode_pipelines.pipes import get_mined_packages_from_checkpoint
from minecode_pipelines.pipes import update_mined_packages_in_checkpoint
from minecode_pipelines.pipes import update_checkpoint_state
from minecode_pipelines.pipes import MINECODE_PIPELINES_CONFIG_REPO
from minecode_pipelines.pipes import INITIAL_SYNC_STATE
from minecode_pipelines.pipes import PERIODIC_SYNC_STATE
from minecode_pipelines.pipes import write_packages_json
from minecode_pipelines.pipes import compress_packages_file
from minecode_pipelines.pipes import decompress_packages_file
from minecode_pipelines.pipes import fetch_checkpoint_by_git

from minecode_pipelines.miners.nix import get_all_nix_packages
from minecode_pipelines.miners.nix import get_all_nix_packages_name
from minecode_pipelines.miners.nix import load_nix_packages
from minecode_pipelines.miners.nix import get_nix_packageurls
from minecode_pipelines.miners.nix import yield_nix_package_data
from minecode_pipelines.miners.nix import NIX_TYPE


from minecode_pipelines.utils import get_temp_dir

from packageurl import PackageURL

from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import delete_local_clone


PACKAGE_FILE_NAME = "NixPackages.json"
COMPRESSED_PACKAGE_FILE_NAME = "NixPackages.json.gz"
NIX_REPLICATE_CHECKPOINT_PATH = "nix/" + PACKAGE_FILE_NAME
COMPRESSED_NIX_REPLICATE_CHECKPOINT_PATH = "nix/" + COMPRESSED_PACKAGE_FILE_NAME
NIX_CHECKPOINT_PATH = "nix/checkpoints.json"
NIX_PACKAGES_CHECKPOINT_PATH = "nix/packages_checkpoint.json"
PACKAGE_BATCH_SIZE = 700

CHANNEL_URL = "https://channels.nixos.org/nixos-unstable/packages.json.br"


def mine_nix_packages(logger=None):
    """
    Mine nix package names from nixos.org and save to checkpoints,
    or get packages from saved checkpoints. We have 3 cases:

    1. first sync: we get latest set of packages from nixos.org and save the
       timestamp to checkpoints.
    2. initial sync: we get packages from checkpoint which we're trying to
       sync up to date
    3. periodic sync: pull in newly released packages from nixos.org.
    """
    nix_checkpoints = fetch_checkpoint_from_github(
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        checkpoint_path=NIX_CHECKPOINT_PATH,
    )
    state = nix_checkpoints.get("state")
    if logger:
        logger(f"Mining state from checkpoint: {state}")

    config_repo = clone_repository(
        repo_url=MINECODE_PIPELINES_CONFIG_REPO,
        clone_path=get_temp_dir(),
        logger=logger,
    )

    packages_dict = {}

    if not state:
        packages_dict = get_all_nix_packages(CHANNEL_URL, logger=logger)
        packages = get_all_nix_packages_name(packages_dict, logger=logger)
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
            cloned_repo=config_repo,
            path=COMPRESSED_NIX_REPLICATE_CHECKPOINT_PATH,
        )

        if logger:
            logger(f"Updating checkpoint mining state to: {INITIAL_SYNC_STATE}")

        update_nix_checkpoints(
            cloned_repo=config_repo,
            state=INITIAL_SYNC_STATE,
            checkpoint_path=NIX_CHECKPOINT_PATH,
            logger=logger,
        )

    elif state == INITIAL_SYNC_STATE:
        if logger:
            logger("Getting packages to sync from nix checkpoint")

        compressed_packages_file = fetch_checkpoint_by_git(
            cloned_repo=config_repo,
            checkpoint_path=COMPRESSED_NIX_REPLICATE_CHECKPOINT_PATH,
        )
        packages_file = decompress_packages_file(
            compressed_packages_file=compressed_packages_file,
            name=PACKAGE_FILE_NAME,
        )

    elif state == PERIODIC_SYNC_STATE:
        packages_dict = get_all_nix_packages(CHANNEL_URL, logger=logger)
        packages = get_all_nix_packages_name(packages_dict, logger=logger)
        packages_file = write_packages_json(
            packages=packages,
            name=PACKAGE_FILE_NAME,
        )

    return packages_dict, packages_file, state, config_repo


def update_nix_checkpoints(
    cloned_repo,
    checkpoint_path,
    state=None,
    config_repo=MINECODE_PIPELINES_CONFIG_REPO,
    logger=None,
):
    checkpoint = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    if state:
        checkpoint["state"] = state

    checkpoint["date"] = str(datetime.now())
    update_checkpoints_in_github(
        checkpoint=checkpoint,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
        logger=logger,
    )


def get_nix_packages_to_sync(packages_file, state, logger=None):
    if logger:
        logger(f"Mining state: {state}")

    packages = load_nix_packages(packages_file)
    if logger:
        logger(f"# of package names fetched from index/checkpoint: {len(packages)}")

    if not packages:
        return

    if not state:
        packages_to_sync = packages
        if logger:
            logger(f"Starting package mining for {len(packages_to_sync)} packages")

        synced_packages = []

    elif state == INITIAL_SYNC_STATE or state == PERIODIC_SYNC_STATE:
        synced_packages = get_mined_packages_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=NIX_PACKAGES_CHECKPOINT_PATH,
        )
        if state == INITIAL_SYNC_STATE:
            packages_to_sync = synced_packages
        else:
            packages_to_sync = list(set(packages).difference(set(synced_packages)))
            if logger:
                logger(
                    f"Starting initial package mining for {len(packages_to_sync)} packages from checkpoint"
                )

    return packages_to_sync, synced_packages


def mine_and_publish_nix_packageurls(packages_dict, packages_to_sync, packages_mined, logger=None):
    if logger:
        logger("Starting package mining for a batch of packages")

    for package_name in packages_to_sync:
        if not package_name:
            continue

        # fetch packageURLs for package
        if logger:
            logger(f"getting packageURLs for package: {package_name}")

        packageurls = get_nix_packageurls(package_name, packages_dict, logger=logger)
        if not packageurls:
            if logger:
                logger(f"Could not fetch package versions for package: {package_name}")
            continue

        purls_and_package_data = yield_nix_package_data(package_name, packageurls)

        base_purl = PackageURL(type=NIX_TYPE, name=package_name).to_string()
        packages_mined.append(package_name)
        if purls_and_package_data:
            yield base_purl, packageurls, purls_and_package_data
        else:
            yield base_purl, packageurls, []


def save_mined_packages_in_checkpoint(packages_mined, synced_packages, config_repo, logger=None):
    # As we are mining the packages to sync with the index,
    # we need to update mined packages checkpoint for every batch
    # so we can continue mining the other packages after restarting
    if logger:
        logger(f"Checkpointing processed packages to: {NIX_PACKAGES_CHECKPOINT_PATH}")

    packages_checkpoint = packages_mined + synced_packages
    update_mined_packages_in_checkpoint(
        packages=packages_checkpoint,
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        cloned_repo=config_repo,
        checkpoint_path=NIX_PACKAGES_CHECKPOINT_PATH,
        logger=logger,
    )


def update_state_and_checkpoints(state, config_repo, logger=None):
    # If we are finished mining all the packages in the initial sync, we can now
    # periodically sync the packages from latest
    if state == INITIAL_SYNC_STATE:
        if logger:
            logger(f"{INITIAL_SYNC_STATE} completed. starting: {PERIODIC_SYNC_STATE}")
        update_checkpoint_state(
            cloned_repo=config_repo,
            state=PERIODIC_SYNC_STATE,
            checkpoint_path=NIX_CHECKPOINT_PATH,
        )

    # If we are finished mining all the packages in the periodic sync, we can now update
    # the last sequence updated
    if state == PERIODIC_SYNC_STATE:
        update_nix_checkpoints(
            cloned_repo=config_repo,
            checkpoint_path=NIX_CHECKPOINT_PATH,
            state=PERIODIC_SYNC_STATE,
            logger=logger,
        )

    # Refresh mined packages checkpoint
    update_checkpoints_in_github(
        checkpoint={"packages_mined": []},
        cloned_repo=config_repo,
        path=NIX_PACKAGES_CHECKPOINT_PATH,
        logger=logger,
    )

    if logger:
        logger(f"Deleting local clone at: {config_repo.working_dir}")
    delete_local_clone(config_repo)
