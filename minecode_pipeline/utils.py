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

from commoncode.fileutils import create_dir


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
