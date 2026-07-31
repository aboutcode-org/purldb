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
from datetime import datetime

import requests
from packageurl import PackageURL
from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import delete_local_clone

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
from minecode_pipelines.utils import get_temp_dir

PACKAGE_FILE_NAME = "NPMPackages.json"
COMPRESSED_PACKAGE_FILE_NAME = "NPMPackages.json.gz"
NPM_REPLICATE_CHECKPOINT_PATH = "npm/" + PACKAGE_FILE_NAME
COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH = "npm/" + COMPRESSED_PACKAGE_FILE_NAME
NPM_CHECKPOINT_PATH = "npm/checkpoints.json"
NPM_PACKAGES_CHECKPOINT_PATH = "npm/packages_checkpoint.json"
PACKAGE_BATCH_SIZE = 700

"""
Visitors for Npmjs and npmjs-like javascript package repositories.

We have this hierarchy in npm replicate and registry index:
    npm projects replicate.npmjs.com (paginated JSON) -> versions at registry.npmjs.org (JSON) -> download urls

See https://github.com/orgs/community/discussions/152515 for information on
the latest replicate.npmjs.com API.

https://replicate.npmjs.com/_all_docs
This NPMJS replicate API serves as an index to get all npm packages and their revision IDs
in paginated queries.

https://replicate.npmjs.com/_changes
This NPMJS replicate API serves as a CHANGELOG of npm packages with update sequences which
can be fetched in paginated queries.

https://registry.npmjs.org/{namespace/name}
For each npm package, a JSON containing details including the list of all releases
and archives, their URLs, and some metadata for each release.

https://registry.npmjs.org/{namespace/name}/{version}
For each release, a JSON contains details for the released version and all the
downloads available for this release.
"""

NPM_REPLICATE_REPO = "https://replicate.npmjs.com/"
NPM_REGISTRY_REPO = "https://registry.npmjs.org/"
NPM_TYPE = "npm"
NPM_REPLICATE_BATCH_SIZE = 10000


def get_package_names_last_key(package_data):
    names = [package.get("id") for package in package_data.get("rows")]
    last_key = package_data.get("rows")[-1].get("key")
    return names, last_key


def get_package_names_last_seq(package_data):
    names = [package.get("id") for package in package_data.get("results")]
    last_seq = package_data.get("last_seq")
    return names, last_seq


def get_current_last_seq(replicate_url=NPM_REPLICATE_REPO):
    npm_replicate_latest_changes = replicate_url + "_changes?descending=True"
    response = requests.get(npm_replicate_latest_changes)
    if not response.ok:
        return

    package_data = response.json()
    _package_names, last_seq = get_package_names_last_seq(package_data)
    return last_seq


def get_updated_npm_packages(last_seq, replicate_url=NPM_REPLICATE_REPO, logger=None):
    all_package_names = []
    i = 0

    while True:
        if logger:
            logger(f"Processing iteration: {i}: changes after seq: {last_seq}")

        npm_replicate_changes = (
            replicate_url + "_changes?" + f"limit={NPM_REPLICATE_BATCH_SIZE}" + f"&since={last_seq}"
        )
        response = requests.get(npm_replicate_changes)
        if not response.ok:
            return all_package_names

        package_data = response.json()
        package_names, last_seq = get_package_names_last_seq(package_data)
        all_package_names.extend(package_names)

        # We have fetched the last set of changes if True
        if len(package_names) < NPM_REPLICATE_BATCH_SIZE:
            break

        i += 1

    return {"packages": all_package_names}, last_seq


def get_npm_packages(replicate_url=NPM_REPLICATE_REPO, logger=None):
    all_package_names = []

    npm_replicate_all = replicate_url + "_all_docs?" + f"limit={NPM_REPLICATE_BATCH_SIZE}"
    response = requests.get(npm_replicate_all)
    if not response.ok:
        return all_package_names

    package_data = response.json()
    package_names, last_key = get_package_names_last_key(package_data)
    all_package_names.extend(package_names)

    total_rows = package_data.get("total_rows")
    iterations = int(total_rows / NPM_REPLICATE_BATCH_SIZE) + 1

    for i in range(iterations):
        npm_replicate_from_id = npm_replicate_all + f'&start_key="{last_key}"'
        if logger:
            logger(f"Processing iteration: {i}: {npm_replicate_from_id}")

        response = requests.get(npm_replicate_from_id)
        if not response.ok:
            raise Exception(npm_replicate_from_id, response.text)

        package_data = response.json()
        package_names, last_key = get_package_names_last_key(package_data)
        all_package_names.extend(package_names)

    return {"packages": all_package_names}


def get_npm_packageurls(name, npm_repo=NPM_REGISTRY_REPO):
    packageurls = []

    project_index_api_url = npm_repo + name
    response = requests.get(project_index_api_url)
    if not response.ok:
        return packageurls

    project_data = response.json()
    versions = project_data.get("versions") or []
    for version in versions:
        purl = PackageURL(
            type=NPM_TYPE,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls


def yield_npm_package_data(name, packageurls=[]):
    for purl in packageurls or get_npm_packageurls(name):
        package_url = PackageURL.from_string(purl)
        package_data_url = NPM_REGISTRY_REPO + name + "/" + package_url.version
        response = requests.get(package_data_url)
        if not response.ok:
            continue
        yield purl, response.json()


def load_npm_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    return packages_data.get("packages", [])


def mine_npm_packages(logger=None):
    """
    Mine npm package names from npm replicate index and save to checkpoints,
    or get packages from saved checkpoints. We have 3 cases:

    1. first sync: we get latest set of packages from the "_all_docs" API endpoint
       of npm replicate and save this and last sequence of the package to checkpoints.
    2. initial sync: we get packages from checkpoint which we're trying to sync up to
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

    config_repo = clone_repository(
        repo_url=MINECODE_PIPELINES_CONFIG_REPO,
        clone_path=get_temp_dir(),
        logger=logger,
    )

    # This is the first time we are syncing from npm replicate
    if not state:
        last_seq = get_current_last_seq(replicate_url=NPM_REPLICATE_REPO)
        if logger:
            logger(
                f"Starting initial checkpointing of packages from npm replicate till seq: {last_seq}"
            )

        packages = get_npm_packages(replicate_url=NPM_REPLICATE_REPO, logger=logger)
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
            path=COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH,
        )

        if logger:
            logger(f"Updating checkpoint mining state to: {INITIAL_SYNC_STATE}")
            logger(f"Updating checkpoint mining last_seq to: {last_seq}")

        update_npm_checkpoints(
            cloned_repo=config_repo,
            state=INITIAL_SYNC_STATE,
            last_seq=last_seq,
            checkpoint_path=NPM_CHECKPOINT_PATH,
            logger=logger,
        )

    elif state == INITIAL_SYNC_STATE:
        if logger:
            logger("Getting packages to sync from npm checkpoint")

        last_seq = fetch_last_seq_mined(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            settings_path=NPM_CHECKPOINT_PATH,
        )

        compressed_packages_file = fetch_checkpoint_by_git(
            cloned_repo=config_repo,
            checkpoint_path=COMPRESSED_NPM_REPLICATE_CHECKPOINT_PATH,
        )
        packages_file = decompress_packages_file(
            compressed_packages_file=compressed_packages_file,
            name=PACKAGE_FILE_NAME,
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
            logger=logger,
        )
        packages_file = write_packages_json(
            packages=packages,
            name=PACKAGE_FILE_NAME,
        )

    return packages_file, state, last_seq, config_repo


def update_npm_checkpoints(
    cloned_repo,
    checkpoint_path,
    state=None,
    last_seq=None,
    config_repo=MINECODE_PIPELINES_CONFIG_REPO,
    logger=None,
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
        logger=logger,
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


def get_npm_packages_to_sync(packages_file, state, logger=None):
    if logger:
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

        synced_packages = []

    elif state == INITIAL_SYNC_STATE or state == PERIODIC_SYNC_STATE:
        synced_packages = get_mined_packages_from_checkpoint(
            config_repo=MINECODE_PIPELINES_CONFIG_REPO,
            checkpoint_path=NPM_PACKAGES_CHECKPOINT_PATH,
        )
        packages_to_sync = list(set(packages).difference(set(synced_packages)))
        if logger:
            logger(
                f"Starting initial package mining for {len(packages_to_sync)} packages from checkpoint"
            )

    return packages_to_sync, synced_packages


def mine_and_publish_npm_packageurls(packages_to_sync, packages_mined, logger=None):
    if logger:
        logger("Starting package mining for a batch of packages")

    for package_name in packages_to_sync:
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

        # this yields a tuple containing purl str, dict containing api info
        purls_and_package_data = yield_npm_package_data(package_name, packageurls)

        base_purl = PackageURL(type=NPM_TYPE, name=package_name).to_string()
        packages_mined.append(base_purl)

        yield base_purl, packageurls, purls_and_package_data


def save_mined_packages_in_checkpoint(packages_mined, synced_packages, config_repo, logger=None):
    # As we are mining the packages to sync with the index,
    # we need to update mined packages checkpoint for every batch
    # so we can continue mining the other packages after restarting
    if logger:
        logger(f"Checkpointing processed packages to: {NPM_PACKAGES_CHECKPOINT_PATH}")

    packages_checkpoint = packages_mined + synced_packages
    update_mined_packages_in_checkpoint(
        packages=packages_checkpoint,
        config_repo=MINECODE_PIPELINES_CONFIG_REPO,
        cloned_repo=config_repo,
        checkpoint_path=NPM_PACKAGES_CHECKPOINT_PATH,
        logger=logger,
    )


def update_state_and_checkpoints(state, last_seq, config_repo, logger=None):
    # If we are finished mining all the packages in the initial sync, we can now
    # periodically sync the packages from latest
    if state == INITIAL_SYNC_STATE:
        if logger:
            logger(f"{INITIAL_SYNC_STATE} completed. starting: {PERIODIC_SYNC_STATE}")
        update_checkpoint_state(
            cloned_repo=config_repo,
            state=PERIODIC_SYNC_STATE,
            checkpoint_path=NPM_CHECKPOINT_PATH,
        )

    # If we are finished mining all the packages in the periodic sync, we can now update
    # the last sequence updated
    if state == PERIODIC_SYNC_STATE:
        if logger:
            logger(f"{PERIODIC_SYNC_STATE} completed. Updating last seq to: {last_seq}")

        update_npm_checkpoints(
            cloned_repo=config_repo,
            checkpoint_path=NPM_CHECKPOINT_PATH,
            state=PERIODIC_SYNC_STATE,
            last_seq=last_seq,
            logger=logger,
        )

    # Refresh mined packages checkpoint
    update_checkpoints_in_github(
        checkpoint={"packages_mined": []},
        cloned_repo=config_repo,
        path=NPM_PACKAGES_CHECKPOINT_PATH,
        logger=logger,
    )

    if logger:
        logger(f"Deleting local clone at: {config_repo.working_dir}")
    delete_local_clone(config_repo)
