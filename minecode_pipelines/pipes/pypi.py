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

import os
import json
import requests

from datetime import datetime

from minecode_pipelines import pipes
from minecode_pipelines.miners.pypi import get_pypi_packages
from minecode_pipelines.miners.pypi import load_pypi_packages
from minecode_pipelines.miners.pypi import get_pypi_packageurls
from minecode_pipelines.miners.pypi import PYPI_REPO

from minecode_pipelines.miners.pypi import PYPI_TYPE

from packageurl import PackageURL

from aboutcode.hashid import get_package_base_dir


from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from scanpipe.pipes.federatedcode import commit_and_push_changes


MINECODE_SETTINGS_REPO = "https://github.com/AyanSinhaMahapatra/minecode-test/"
PYPI_SETTINGS_PATH = "minecode_checkpoints/pypi.json"


def mine_pypi_packages(logger=None):
    return get_pypi_packages(pypi_repo=PYPI_REPO, logger=logger)


def fetch_last_serial_mined(
    settings_repo=MINECODE_SETTINGS_REPO,
    settings_path=PYPI_SETTINGS_PATH,
):
    """
    Fetch "last_serial" for the last mined packages.

    This is a simple JSON in a github repo containing mining checkpoints
    with the "last_serial" from the pypi index which was mined. Example:
    https://github.com/AyanSinhaMahapatra/minecode-test/blob/main/minecode_checkpoints/pypi.json
    """
    repo_name = settings_repo.split("github.com")[-1]
    minecode_checkpoint_pypi = (
        "https://raw.githubusercontent.com/" + repo_name + "refs/heads/main/" + settings_path
    )
    response = requests.get(minecode_checkpoint_pypi)
    if not response.ok:
        return

    settings_data = json.loads(response.text)
    return settings_data.get("last_serial")


def update_last_serial_mined(
    last_serial,
    settings_repo=MINECODE_SETTINGS_REPO,
    settings_path=PYPI_SETTINGS_PATH,
):
    settings_data = {
        "date": str(datetime.now()),
        "last_serial": last_serial,
    }
    cloned_repo = clone_repository(repo_url=settings_repo)
    settings_path = os.path.join(cloned_repo.working_dir, settings_path)
    pipes.write_data_to_file(path=settings_path, data=settings_data)
    commit_and_push_changes(repo=cloned_repo, file_to_commit=settings_path)


def mine_and_publish_pypi_packageurls(packages, use_last_serial=False, logger=None):
    if use_last_serial:
        last_serial_fetched = fetch_last_serial_mined()
        if logger:
            logger(f"Last serial number mined: {last_serial_fetched}")

    last_serial, packages = load_pypi_packages(packages)
    if logger:
        logger(f"Last serial number fetched from index: {last_serial}")
        logger(f"# of package names fetched from index: {len(packages)}")

    # We are all synced up from the index
    if use_last_serial and last_serial <= last_serial_fetched:
        return

    if packages:
        # clone repo
        cloned_repo = clone_repository(repo_url=MINECODE_SETTINGS_REPO)
        if logger:
            logger(f"{MINECODE_SETTINGS_REPO} repo cloned at: {cloned_repo.working_dir}")

    purl_files_updated = []
    for package in packages:
        last_serial = package.get("_last-serial")

        # we skip updating this package if it was not updated
        # after our latest sync
        if use_last_serial and last_serial <= last_serial_fetched:
            continue

        # fetch packageURLs for package
        name = package.get("name")
        if logger:
            logger(f"getting packageURLs for package: {name}")

        packageurls = get_pypi_packageurls(name)
        if not packageurls:
            continue

        # get repo and path for package
        base_purl = PackageURL(type=PYPI_TYPE, name=name).to_string()
        package_base_dir = get_package_base_dir(purl=base_purl)

        if logger:
            logger(f"writing packageURLs for package: {base_purl} at: {package_base_dir}")
            purls_string = " ".join(packageurls)
            logger(f"packageURLs: {purls_string}")

        # write packageURLs to file
        purl_file = pipes.write_packageurls_to_file(
            repo=cloned_repo,
            base_dir=package_base_dir,
            packageurls=packageurls,
        )
        purl_files_updated.append(purl_file)

        # commit changes
        commit_changes(repo=cloned_repo, file_to_commit=purl_file, purl=base_purl)

    # Push changes to remote repository
    push_changes(repo=cloned_repo)

    # update last_serial to minecode checkpoints
    if use_last_serial:
        update_last_serial_mined(last_serial=last_serial)
