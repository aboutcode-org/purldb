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
from pathlib import Path

import requests
import saneyaml

from aboutcode.hashid import PURLS_FILENAME

# states:
# note: a state is null when mining starts
INITIAL_SYNC_STATE = "initial-sync"
PERIODIC_SYNC_STATE = "periodic-sync"


MINECODE_PIPELINES_CONFIG_REPO = "https://github.com/aboutcode-data/minecode-pipelines-config/"


def fetch_checkpoint_from_github(config_repo, checkpoint_path):
    repo_name = config_repo.split("github.com")[-1]
    checkpoints_file = (
        "https://raw.githubusercontent.com/" + repo_name + "refs/heads/main/" + checkpoint_path
    )
    response = requests.get(checkpoints_file)
    if not response.ok:
        return

    checkpoint_data = json.loads(response.text)
    return checkpoint_data


def get_checkpoint_from_file(cloned_repo, path):
    checkpoint_path = os.path.join(cloned_repo.working_dir, path)
    with open(checkpoint_path) as f:
        checkpoint_data = json.load(f)
    return checkpoint_data or {}


def update_checkpoints_in_github(checkpoint, cloned_repo, path):
    from scanpipe.pipes.federatedcode import commit_and_push_changes

    checkpoint_path = os.path.join(cloned_repo.working_dir, path)
    write_data_to_json_file(path=checkpoint_path, data=checkpoint)
    commit_message = """Update federatedcode purl mining checkpoint"""
    commit_and_push_changes(
        repo=cloned_repo,
        files_to_commit=[checkpoint_path],
        commit_message=commit_message,
    )


def get_mined_packages_from_checkpoint(config_repo, checkpoint_path):
    checkpoint = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    return checkpoint.get("packages_mined", [])


def update_mined_packages_in_checkpoint(packages, config_repo, cloned_repo, checkpoint_path):
    mined_packages = get_mined_packages_from_checkpoint(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )
    packages = {"packages_mined": packages + mined_packages}
    update_checkpoints_in_github(
        checkpoint=packages,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
    )


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    write_data_to_yaml_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def write_data_to_yaml_file(path, data):
    if isinstance(path, str):
        path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))


def write_data_to_json_file(path, data):
    if isinstance(path, str):
        path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def delete_cloned_repos(repos, logger=None):
    from scanpipe.pipes.federatedcode import delete_local_clone

    if not repos:
        return

    for repo in repos:
        if logger:
            logger(f"Deleting local clone at: {repo.working_dir}")
        delete_local_clone(repo)
