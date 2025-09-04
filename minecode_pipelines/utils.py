#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import tempfile
import os
from commoncode.fileutils import create_dir
from git import Repo

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


def get_changed_files(
    repo: Repo, commit_x: str = "4b825dc642cb6eb9a060e54bf8d69288fbee4904", commit_y: str = None
):
    """
    Return a list of files changed between two commits using GitPython.
    Includes added, modified, deleted, and renamed files.

    - commit_x is the empty tree hash (repo root).
    - commit_y is the latest commit (HEAD).
    """

    if commit_y is None:
        commit_y = repo.head.commit.hexsha

    commit_x_obj = repo.commit(commit_x)
    commit_y_obj = repo.commit(commit_y)

    diff_index = commit_x_obj.diff(commit_y_obj)
    changed_files = {item.a_path or item.b_path for item in diff_index}

    return list(changed_files)
