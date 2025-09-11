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
import saneyaml

from datetime import datetime
from pathlib import Path

from aboutcode.hashid import PURLS_FILENAME
from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import commit_and_push_changes


MINECODE_SETTINGS_REPO = "https://github.com/AyanSinhaMahapatra/minecode-test/"


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    write_data_to_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def write_data_to_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))


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


def update_last_serial_mined(
    last_serial,
    settings_repo=MINECODE_SETTINGS_REPO,
    settings_path=None,
):
    settings_data = {
        "date": str(datetime.now()),
        "last_serial": last_serial,
    }
    cloned_repo = clone_repository(repo_url=settings_repo)
    settings_path = os.path.join(cloned_repo.working_dir, settings_path)
    write_data_to_file(path=settings_path, data=settings_data)
    commit_and_push_changes(repo=cloned_repo, file_to_commit=settings_path)
