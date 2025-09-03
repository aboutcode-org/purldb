#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import textwrap
from pathlib import Path
import saneyaml
from aboutcode import hashid

ALLOWED_HOST = "ALLOWED_HOST"
VERSION = "ALLOWED_HOST"
author_name = "FEDERATEDCODE_GIT_SERVICE_NAME"
author_email = "FEDERATEDCODE_GIT_SERVICE_EMAIL"
remote_name = "origin"


def write_purls_to_repo(repo, package, packages_yaml, push_commit=False):
    """Write or update package purls in the repo and optionally commit/push changes."""

    ppath = hashid.get_package_purls_yml_file_path(package)
    add_purl_result(packages_yaml, repo, ppath)

    if push_commit:
        change_type = "Add" if ppath in repo.untracked_files else "Update"
        commit_message = f"""\
        {change_type} list of available {package} versions
        Tool: pkg:github/aboutcode-org/purldb@v{VERSION}
        Reference: https://{ALLOWED_HOST}/
        Signed-off-by: {author_name} <{author_email}>
        """

        default_branch = repo.active_branch.name
        repo.index.commit(textwrap.dedent(commit_message))
        repo.git.push(remote_name, default_branch, "--no-verify")


def add_purl_result(purls, repo, purls_file):
    """Add package urls result to the local Git repository."""
    relative_purl_file_path = Path(*purls_file.parts[1:])

    write_to = Path(repo.working_dir) / relative_purl_file_path
    write_to.parent.mkdir(parents=True, exist_ok=True)

    with open(purls_file, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(purls))

    repo.index.add([relative_purl_file_path])
    return relative_purl_file_path
