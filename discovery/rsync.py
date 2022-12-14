#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import collections
import logging
import re

import arrow
from dateutil import tz

from discovery import command
from discovery.utils import get_temp_file

logger = logging.getLogger(__name__)
# import sys
# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
# logger.setLevel(logging.DEBUG)

RSYNC_COMMAND = 'rsync'


def modules(input_file):
    """
    Yield rsync modules by parsing rsync output in file input_file.
    Should be based on the output of running rsync without destination,
    no arguments (in particular do not use --no-motd) and a source url without
    extra path such as:
        rsync rsync://mirrors.ibiblio.org
    """
    with open(input_file) as inp:
        for line in inp:
            if not line:
                continue
            if line.startswith(' '):
                # this is the motd section
                continue
            line = line.strip()
            if line:
                name, _desc = line.split('\t', 1)
                yield name.strip()


octals = re.compile(r'#(\d{3})').findall


def decode_path(p):
    """Decode an rsync path with octal encodings"""
    for oc in set(octals(p)):
        p = p.replace('#' + oc, octal2char(oc))
    return p


def octal2char(s):
    """Convert the rsync octal-encoded representation to a char"""
    return chr(int(s, 8))


def decode_ts(s):
    """
    Convert an rsync timestamp (which is local tz) to an UTC ISO timestamp.
    """
    tzinfo = tz.tzutc()
    ar = arrow.get(s, 'YYYY/MM/DD HH:mm:ss').replace(tzinfo=tzinfo).to('utc')
    return ar.isoformat()

# note: there is a large number of possible file types, but we do not care for
# them: only files and dirs matter; And links, block, pipes, fifo, etc do not.
# i.e. we keep only - and d


rsync_line = re.compile(
    r'^(?P<type>[\-d])'
    r'(?P<perm>.{9})'
    r' +'
    r'(?P<size>[\d,]+)'
    r' '
    r'(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})'  # YYYY/MM/DD HH:mm:ss
    r' +'
    r'(?P<path>.+$)'
).match

Entry = collections.namedtuple('Entry', 'type perm size date path')


def entry(line):
    """
    Return an Entry constructed from an rsync directory listing line. Assumes
    universal line endings.
    """
    line = line.rstrip('\n')
    if not line:
        return
    if 'skipping directory' in line:
        return
    rline = rsync_line(line)
    if not rline:
        return
    typ = rline.group('type')
    perm = rline.group('perm')
    size = int(rline.group('size').replace(',', ''))
    ts = rline.group('ts')
    date = decode_ts(ts)
    path = rline.group('path')
    path = decode_path(path)
    return dict(Entry(typ, perm, size, date, path)._asdict())


def directory_entries(listing_location):
    """
    Yield rsync directory Entry by parsing rsync output store at
    `listing_location` location.
    """
    with open(listing_location) as inp:
        for line in inp:
            try:
                e = entry(line)
                if e:
                    yield e
            except ValueError:
                # FIXME: why???
                continue


def fetch_directory(uri, recurse=True):
    """
    Return the location of a tempfile containing an rsync dir listing for uri.
    Recursive if recurse is True. Raise an Exception with error details.
    """
    temp_file = get_temp_file(file_name='minecode-rsync-dir-', extension='.rsync')
    with open(temp_file, 'w') as tmp:
        file_name = tmp.name
        ends = not uri.endswith('/') and '/' or ''
        recursive = recurse and '--recursive' or '--no-recursive'
        cmd = 'rsync --no-motd %(recursive)s -d "%(uri)s%(ends)s"' % locals()
        rsync = command.Command(cmd)
        out, err = rsync.execute()

        for o in out:
            tmp.write(o)

        err = '\n'.join([e for e in err])
        rc = rsync.returncode
        if err or rc:
            raise Exception('%(cmd) failed. rc:%(tc)d err: %(err)s' % locals())
        else:
            return file_name
