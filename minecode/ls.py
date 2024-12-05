#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import posixpath
import stat
from datetime import datetime
from functools import total_ordering

from ftputil.error import ParserError
from ftputil.stat import UnixParser

TRACE = False

logger = logging.getLogger(__name__)
if TRACE:
    import sys

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    logger.setLevel(logging.DEBUG)

"""
Parse directory listings such as a find or ls command output.
These are commonly provided as file indexes in package repositories.
"""

# TODO: use constants for entry types
DIR = "d"
FILE = "f"
LINK = "l"
SPECIAL = "s"

# FIXME: do we really need link and special file support?


@total_ordering
class Entry:
    """Represent a file, directory or link entry in a directory listing."""

    __slots__ = "path", "type", "size", "date", "target"

    def __init__(self, path=None, type=None, size=None, date=None, target=None):  # NOQA
        self.path = path
        self.type = type
        self.size = size
        self.date = date
        self.target = target
        if TRACE:
            logger.debug("Entry(): " + repr(self))

    def __repr__(self):
        base = "Entry(path=%(path)r, type=%(type)r, size=%(size)r, date=%(date)r"
        link_target = ")"
        if self.type == LINK:
            link_target = ", target=%(target)r)"
        return (base + link_target) % self.to_dict()

    def __eq__(self, other):
        return isinstance(other, Entry) and self.to_dict() == other.to_dict()

    def __lt__(self, other):
        return isinstance(other, Entry) and tuple(self.to_dict().items()) < tuple(
            other.to_dict().items()
        )

    def __hash__(self):
        return hash(tuple(self.to_dict().items()))

    def to_dict(self):
        return {
            "path": self.path,
            "type": self.type,
            "size": self.size,
            "date": self.date,
            "target": self.target,
        }

    @classmethod
    def from_stat(self, stat_result, base_dir="", use_utc_time=True):
        """
        Return a new Entry built from a stat-like tuple and a base
        directory.
        """
        res_type = None
        path = stat_result._st_name
        path = clean_path(path)

        # ignore date and size unless a file
        date = None
        size = 0

        target = None
        mode = stat_result.st_mode

        if stat.S_ISREG(mode):
            res_type = FILE
            if use_utc_time:
                utc_date = datetime.utcfromtimestamp(stat_result.st_mtime)
            else:
                utc_date = datetime.fromtimestamp(stat_result.st_mtime)
            date = datetime.isoformat(utc_date)[:10]
            size = stat_result.st_size

        elif stat.S_ISDIR(mode):
            res_type = DIR

        elif stat.S_ISLNK(mode):
            res_type = LINK
            target = stat_result._st_target

        else:
            # anything else is some special file of sorts
            res_type = SPECIAL

        # rejoin path with base-dir if any
        if base_dir and base_dir != ".":
            base_dir = clean_path(base_dir)
            path = posixpath.join(base_dir, path)

        return Entry(path, res_type, size, date, target)


def clean_path(path):
    """Return a path cleaned from leading and trailing slashes and leading ./."""
    path = path.strip().strip("/")
    if path.startswith("./"):
        path = path[2:]
    return path.strip()


def remove_inode(line):
    """
    Return the line with leading inode number and size in block (which are
    numbers separated by spaces) are removed.
    """
    _, _, line = line.strip().partition(" ")
    _, _, line = line.strip().partition(" ")
    return line.strip()


def parse_directory_listing(dir_listing, from_find=False):
    """
    Yield Entry from a `dir_listing` directory listing text.

    If`from_find` is True the directory listing is assumed to come from a "find
    -ls" command. Otherwise it is assumed to come from an "ls -alR" command.

    For "find -ls" all lines start with an inode number, e.g. a set of digits.
    Note: the "find -ls" is similar to the "ls -ils" format (except for paths):
    we have an inode and size in block prefixing each listing line.
    """
    lines = dir_listing.splitlines()
    parser = UnixParser()

    # default in case this would not be a recursive listing: we always need a base dir
    base_dir = ""
    for ln, line in enumerate(lines, 1):
        line = line.strip()
        if parser.ignores_line(line):
            continue

        if from_find:
            line = remove_inode(line)

        file_stat = None
        try:
            file_stat = parser.parse_line(line)
            if TRACE:
                logger.debug("parse_directory_listing:file_stat: " + repr(file_stat))
                dt = datetime.utcfromtimestamp(file_stat.st_mtime)
                dt = datetime.isoformat(dt)
                logger.debug("parse_directory_listing:file_stat:date: " + repr(dt))

        except ParserError:
            # this is likely a directory line from an ls -LR listing. Strip
            # trailing colon and keep track of the base directory
            if not line.endswith(":"):
                raise Exception(f"Unknown directory listing line format: #{ln}: {line}")
            base_dir = line.strip(":")
            continue

        if file_stat._st_name in (".", ".."):
            continue

        entry = Entry.from_stat(file_stat, base_dir=base_dir, use_utc_time=False)
        if entry:
            yield entry
