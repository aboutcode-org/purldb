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
from git import Repo

from scanpipe.pipes.federatedcode import delete_local_clone
from scanpipe.pipes.federatedcode import commit_and_push_changes

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
        return {}

    checkpoint_data = json.loads(response.text)
    return checkpoint_data


def get_checkpoint_from_file(cloned_repo, path):
    checkpoint_path = os.path.join(cloned_repo.working_dir, path)
    with open(checkpoint_path) as f:
        checkpoint_data = json.load(f)
    return checkpoint_data or {}


def update_checkpoints_in_github(checkpoint, cloned_repo, path):
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


def write_packageurls_to_file(repo, base_dir, packageurls, append=False):
    if not isinstance(packageurls, list):
        raise Exception("`packageurls` needs to be a list")

    purl_file_rel_path = os.path.join(base_dir, PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    if append and purl_file_full_path.exists():
        existing_purls = load_data_from_yaml_file(purl_file_full_path)
        packageurls = existing_purls.extend(packageurls)
    write_data_to_yaml_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def load_data_from_yaml_file(path):
    if isinstance(path, str):
        path = Path(path)

    with open(path, encoding="utf-8") as f:
        return saneyaml.load(f.read())


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
    if not repos:
        return

    for repo in repos:
        if logger:
            logger(f"Deleting local clone at: {repo.working_dir}")
        delete_local_clone(repo)


def get_changed_files(repo: Repo, commit_x: str = None, commit_y: str = None):
    """
    Return a list of files changed between two commits using GitPython.
    Includes added, modified, deleted, and renamed files.
    - commit_x: base commit (or the empty tree hash for the first commit)
    - commit_y: target commit (defaults to HEAD if not provided)
    """
    EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    if commit_y is None:
        commit_y = repo.head.commit.hexsha
    commit_y_obj = repo.commit(commit_y)

    if commit_x is None or commit_x == EMPTY_TREE_HASH:
        # First commit case: diff against empty tree
        diff_index = commit_y_obj.diff(EMPTY_TREE_HASH, R=True)
    else:
        commit_x_obj = repo.commit(commit_x)
        diff_index = commit_x_obj.diff(commit_y_obj, R=True)

    changed_files = {item.a_path or item.b_path for item in diff_index}
    return list(changed_files)


def get_last_commit(repo, ecosystem):
    """
    Retrieve the last mined commit for a given ecosystem.
    This function reads a JSON checkpoint file from the repository, which stores
    mining progress. Each checkpoint contains the "last_commit" from the package
    index (e.g., PyPI) that was previously mined.
    https://github.com/AyanSinhaMahapatra/minecode-test/blob/main/minecode_checkpoints/pypi.json
    https://github.com/ziadhany/cargo-test/blob/main/minecode_checkpoints/cargo.json
    """

    last_commit_file_path = (
        Path(repo.working_tree_dir) / "minecode_checkpoints" / f"{ecosystem}.json"
    )
    try:
        with open(last_commit_file_path) as f:
            settings_data = json.load(f)
    except FileNotFoundError:
        return
    return settings_data.get("last_commit")


def get_commit_at_distance_ahead(
    repo: Repo,
    current_commit: str,
    num_commits_ahead: int = 10,
    branch_name: str = "master",
) -> str:
    """
    Return the commit hash that is `num_commits_ahead` commits ahead of `current_commit`
    on the given branch.
    """
    if not current_commit:
        current_commit = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    revs = repo.git.rev_list(f"^{current_commit}", branch_name).splitlines()
    if len(revs) < num_commits_ahead:
        raise ValueError(f"Not enough commits ahead; only {len(revs)} available.")
    return revs[-num_commits_ahead]
