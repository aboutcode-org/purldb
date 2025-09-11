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
import textwrap
from datetime import datetime
from pathlib import Path

import saneyaml
from aboutcode import hashid
from git import Repo
from scanpipe.pipes import federatedcode


MINECODE_SETTINGS_REPO = "https://github.com/AyanSinhaMahapatra/minecode-test/"
VERSION = os.environ.get("VERSION", "")
PURLDB_ALLOWED_HOST = os.environ.get("FEDERATEDCODE_GIT_ALLOWED_HOST", "")
author_name = os.environ.get("FEDERATEDCODE_GIT_SERVICE_NAME", "")
author_email = os.environ.get("FEDERATEDCODE_GIT_SERVICE_EMAIL", "")
remote_name = os.environ.get("FEDERATEDCODE_GIT_REMOTE_NAME", "origin")


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, hashid.PURLS_FILENAME)
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
    cloned_repo = federatedcode.clone_repository(repo_url=settings_repo)
    settings_path = os.path.join(cloned_repo.working_dir, settings_path)
    write_data_to_file(path=settings_path, data=settings_data)
    federatedcode.commit_and_push_changes(repo=cloned_repo, file_to_commit=settings_path)


def write_purls_to_repo(repo, package, packages, push_commit=False):
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


def write_json_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def write_purls_to_repo(repo, package, updated_purls, push_commits=False):
    """Write or update package purls in the repo and optionally commit/push changes."""
    ppath = hashid.get_package_purls_yml_file_path(package)
    git_stage_purls(updated_purls, repo, ppath)
    if push_commits:
        commit_and_push_changes(repo)


def git_stage_purls(purls, repo, purls_file):
    """Write package URLs to a file and stage it in the local Git repository."""
    relative_purl_file_path = Path(purls_file)

    write_to = Path(repo.working_dir) / relative_purl_file_path

    write_data_to_file(path=write_to, data=purls)

    repo.index.add([relative_purl_file_path])
    return relative_purl_file_path


def commit_and_push_changes(repo):
    """
    Commit staged changes to the local repository and push them
    to the remote on the current active branch.
    """

    commit_message = f"""\
    Add/Update list of available package versions
    Tool: pkg:github/aboutcode-org/purldb@v{VERSION}
    Reference: https://{PURLDB_ALLOWED_HOST}/
    Signed-off-by: {author_name} <{author_email}>
    """

    default_branch = repo.active_branch.name
    repo.index.commit(textwrap.dedent(commit_message))
    repo.git.push(remote_name, default_branch, "--no-verify")


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


def update_last_commit(last_commit, repo, ecosystem):
    """Update the last mined commit checkpoint for a given ecosystem and push it to the repo."""

    settings_data = {
        "date": str(datetime.now()),
        "last_commit": last_commit,
    }

    settings_path = Path(repo.working_tree_dir) / "minecode_checkpoints" / f"{ecosystem}.json"
    write_json_file(path=settings_path, data=settings_data)
    repo.index.add([settings_path])

    commit_message = f"""\
    Update last mined commit for {ecosystem}

    Tool: pkg:github/aboutcode-org/purldb@v{VERSION}
    Reference: https://{PURLDB_ALLOWED_HOST}/
    Signed-off-by: {author_name} <{author_email}>
    """

    default_branch = repo.active_branch.name
    repo.index.commit(textwrap.dedent(commit_message))
    repo.git.push(remote_name, default_branch, "--no-verify")
