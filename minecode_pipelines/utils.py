#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import tempfile
import textwrap
from pathlib import Path

from commoncode.fileutils import create_dir
from minecode_pipelines.miners import write_data_to_file

VERSION = os.environ.get("VERSION", "")
PURLDB_ALLOWED_HOST = os.environ.get("FEDERATEDCODE_GIT_ALLOWED_HOST", "")
author_name = os.environ.get("FEDERATEDCODE_GIT_SERVICE_NAME", "")
author_email = os.environ.get("FEDERATEDCODE_GIT_SERVICE_EMAIL", "")
remote_name = os.environ.get("FEDERATEDCODE_GIT_REMOTE_NAME", "origin")

from itertools import zip_longest


def grouper(n, iterable, padvalue=None):
    """
    Produce batches of length `n` for an `iterable`.
    https://docs.python.org/3.10/library/itertools.html#itertools-recipes

    #TODO: replace with `itertools.batched` added in python3.12
    """
    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)


def system_temp_dir(temp_dir=os.getenv("MINECODE_TMP")):
    """Return the global temp directory.."""
    if not temp_dir:
        temp_dir = os.path.join(tempfile.gettempdir(), "minecode")
    create_dir(temp_dir)
    return temp_dir


def get_temp_dir(base_dir="", prefix=""):
    """
    Return the path to base a new unique temporary directory, created under
    the system-wide `system_temp_dir` temp directory and as a subdir of the
    base_dir path, a path relative to the `system_temp_dir`.
    """
    if base_dir:
        base_dir = os.path.join(system_temp_dir(), base_dir)
        create_dir(base_dir)
    else:
        base_dir = system_temp_dir()
    return tempfile.mkdtemp(prefix=prefix, dir=base_dir)


def get_temp_file(file_name="data", extension=".file", dir_name=""):
    """
    Return a file path string to a new, unique and non-existing
    temporary file that can safely be created without a risk of name
    collision.
    """
    if extension and not extension.startswith("."):
        extension = "." + extension

    file_name = file_name + extension
    # create a new temp dir each time
    temp_dir = get_temp_dir(dir_name)
    location = os.path.join(temp_dir, file_name)
    return location


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
