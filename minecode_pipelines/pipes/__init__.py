#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from aboutcode.hashid import PURLS_FILENAME
import os
import textwrap
from pathlib import Path
import saneyaml
from aboutcode import hashid

VERSION = os.environ.get("VERSION", "")
PURLDB_ALLOWED_HOST = os.environ.get("FEDERATEDCODE_GIT_ALLOWED_HOST", "")
author_name = os.environ.get("FEDERATEDCODE_GIT_SERVICE_NAME", "")
author_email = os.environ.get("FEDERATEDCODE_GIT_SERVICE_EMAIL", "")
remote_name = os.environ.get("FEDERATEDCODE_GIT_REMOTE_NAME", "origin")


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    write_data_to_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def write_data_to_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))


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
