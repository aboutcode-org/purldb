#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os
import requests
from datetime import datetime

import saneyaml
from aboutcode import hashid
from scanpipe.pipes import federatedcode


MINECODE_SETTINGS_REPO = "https://github.com/AyanSinhaMahapatra/minecode-test/"


def fetch_last_serial_mined(
    settings_repo=MINECODE_SETTINGS_REPO,
    settings_path=None,
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


def write_data_to_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))


def update_last_serial_mined(
    last_serial,
    settings_repo=MINECODE_SETTINGS_REPO,
    settings_path=None,
):
    settings_data = {
        "date": str(datetime.now()),
        "last_serial": last_serial,
    }
    cloned_repo = federatedcode.clone_repository(repo_url=settings_repo)
    settings_path = os.path.join(cloned_repo.working_dir, settings_path)
    write_data_to_file(path=settings_path, data=settings_data)
    federatedcode.commit_and_push_changes(repo=cloned_repo, file_to_commit=settings_path)


def create_package_path(package):
    path_elements = hashid.package_path_elements(package)
    _, core_path, _, _ = path_elements
    ppath = core_path / hashid.PURLS_FILENAME
    return ppath


def write_purls_to_repo(repo, package, packages, commit_message="",push_commit=False):
    # save purls to yaml
    path_elements = hashid.package_path_elements(package)
    _, core_path, _, _ = path_elements
    ppath = core_path / hashid.PURLS_FILENAME
    purls = [p.purl for p in packages]
    federatedcode.write_data_as_yaml(
        base_path=repo.working_dir,
        file_path=ppath,
        data=purls,
    )

    change_type = "Add" if ppath in repo.untracked_files else "Update"
    commit_message = f"""\
    {change_type} list of available {package} versions
    """
    federatedcode.commit_changes(
        repo=repo,
        files_to_commit=[ppath],
        commit_message=commit_message,
    )

    # see if we should push
    if push_commit:
        federatedcode.push_changes(repo=repo)
