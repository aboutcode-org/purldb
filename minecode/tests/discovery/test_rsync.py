#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

# 
from unittest import skipIf
import os

from discovery import rsync
from discovery import ON_WINDOWS
from discovery.utils_test import MiningTestCase


class RsyncTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_modules(self):
        inp = self.get_test_loc('rsync/rsync_modules')
        output = list(rsync.modules(inp))
        expected = '''apache CPAN CTAN eclipse flightgear gnualpha gnuftp
                      mozdev mozilla opencsw simgear sugar xemacs'''.split()
        self.assertEquals(expected, output)

    def test_entry_rsync_31(self):
        # $ rsync --no-motd --recursive rsync/rsync_dir/
        lines = [
            'drwxrwxr-x          4,096 2015/07/23 17:36:47 .',
            '-rw-rw-r--              0 2015/07/23 17:36:47 foo',
            'drwxrwxr-x          4,096 2015/07/23 17:36:47 bar',
            '-rw-rw-r--              0 2015/07/23 17:36:47 bar/this',
            'drwxrwxr-x          4,096 2015/07/23 17:36:47 bar/that',
            '-rw-rw-r--              0 2015/07/23 17:36:47 bar/that/baz',
        ]
        expected = [
            rsync.Entry('d', 'rwxrwxr-x', 4096, '2015-07-23T17:36:47+00:00', '.')._asdict(),
            rsync.Entry('-', 'rw-rw-r--', 0, '2015-07-23T17:36:47+00:00', 'foo')._asdict(),
            rsync.Entry('d', 'rwxrwxr-x', 4096, '2015-07-23T17:36:47+00:00', 'bar')._asdict(),
            rsync.Entry('-', 'rw-rw-r--', 0, '2015-07-23T17:36:47+00:00', 'bar/this')._asdict(),
            rsync.Entry('d', 'rwxrwxr-x', 4096, '2015-07-23T17:36:47+00:00', 'bar/that')._asdict(),
            rsync.Entry('-', 'rw-rw-r--', 0, '2015-07-23T17:36:47+00:00', 'bar/that/baz')._asdict(),
        ]

        for test, exp in zip(lines, expected):
            result = rsync.entry(test)
            self.assertEquals(exp, result)

    def test_entry(self):
        lines = [
            '-rw-r--r--     4399746 2008/11/23 16:03:57 zz/ZZUL P/ZUL.gz',
            'drwxrwxr-x        4096 2004/08/09 00:47:02 pub/sou/a/a7',
            '-rwxrwxr-x        4096 2004/08/09 00:47:02 pub/#345sou/a/a7',
            'lrwxrwxrwx          19 2007/11/22 11:37:54 s/c/a/index.html',
            'crwxrwxrwx          19 2007/11/22 11:37:54 dev/pts1',
        ]

        expected = [
            rsync.Entry('-', 'rw-r--r--', 4399746, '2008-11-23T16:03:57+00:00', 'zz/ZZUL P/ZUL.gz')._asdict(),
            rsync.Entry('d', 'rwxrwxr-x', 4096, '2004-08-09T00:47:02+00:00', 'pub/sou/a/a7')._asdict(),
            rsync.Entry('-', 'rwxrwxr-x', 4096, '2004-08-09T00:47:02+00:00', 'pub/\xe5sou/a/a7')._asdict(),
            None,
            None,
        ]

        for test, exp in zip(lines, expected):
            result = rsync.entry(test)
            self.assertEquals(exp, result)

    def test_directory(self):
        test_dir = self.get_test_loc('rsync/rsync_wicket.dir')
        output = list(rsync.directory_entries(test_dir))

        expected = [
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-03-18T19:02:46+00:00', path='.'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=5, date='2014-03-18T19:02:46+00:00', path='.revision'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-02-05T09:34:20+00:00', path='1.4.23'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=95314, date='2014-02-05T09:23:44+00:00', path='1.4.23/CHANGELOG-1.4'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=3712820, date='2014-02-05T09:23:44+00:00', path='1.4.23/apache-wicket-1.4.23-source.tgz'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-02-05T09:34:20+00:00', path='1.4.23/binaries'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=23622515, date='2014-02-05T09:23:44+00:00', path='1.4.23/binaries/apache-wicket-1.4.23.tar.gz'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=32524295, date='2014-02-05T09:23:44+00:00', path='1.4.23/binaries/apache-wicket-1.4.23.zip'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-01-27T09:09:40+00:00', path='1.5.11'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=115587, date='2014-01-20T16:53:10+00:00', path='1.5.11/CHANGELOG-1.5'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=4116809, date='2014-01-20T16:53:10+00:00', path='1.5.11/apache-wicket-1.5.11-source.tgz'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-01-27T09:09:39+00:00', path='1.5.11/binaries'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=26048500, date='2014-01-20T16:53:10+00:00', path='1.5.11/binaries/apache-wicket-1.5.11.tar.gz'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=36156260, date='2014-01-20T16:53:10+00:00', path='1.5.11/binaries/apache-wicket-1.5.11.zip'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-02-19T08:36:07+00:00', path='6.14.0'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=78058, date='2014-02-14T15:51:23+00:00', path='6.14.0/CHANGELOG-6.x'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=4792619, date='2014-02-14T15:51:23+00:00', path='6.14.0/apache-wicket-6.14.0.tar.gz'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=9038442, date='2014-02-14T15:51:23+00:00', path='6.14.0/apache-wicket-6.14.0.zip'),
            rsync.Entry(type='d', perm='rwxrwxr-x', size=4096, date='2014-02-19T08:36:05+00:00', path='6.14.0/binaries'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=29851252, date='2014-02-14T15:51:23+00:00', path='6.14.0/binaries/apache-wicket-6.14.0-bin.tar.gz'),
            rsync.Entry(type='-', perm='rw-rw-r--', size=29890658, date='2014-02-14T15:51:23+00:00', path='6.14.0/binaries/apache-wicket-6.14.0-bin.zip')
        ]
        expected = [dict(x._asdict()) for x in expected]
        self.assertEquals(expected, output)

    def test_directory_weird_file_types_are_ignored(self):
        self.maxDiff = None
        inp = self.get_test_loc('rsync/rsync_dev.dir')
        output = rsync.directory_entries(inp)
        results = [e['path'] for e in output if e['type'] == '-']
        expected = ['dev/.udev/rules.d/root.rules']
        self.assertEquals(expected, results)

    @skipIf(ON_WINDOWS, 'rsync is not available on windows')
    def test_fetch_directory(self):
        self.maxDiff = None
        inp = self.get_test_loc('rsync/rsync_dir')
        output = rsync.fetch_directory(inp)
        expected = 'foo bar bar/this bar/that bar/that/baz'.split()
        with open(output) as f:
            results = f.read()
            self.assertTrue(all(e in results for e in expected))

    @skipIf(ON_WINDOWS, 'rsync is not available on windows')
    def test_fetch_directory_no_recurse(self):
        self.maxDiff = None
        inp = self.get_test_loc('rsync/rsync_dir')
        output = rsync.fetch_directory(inp, recurse=False)
        expected = ['foo', 'bar']

        with open(output) as f:
            results = f.read()
            self.assertTrue(all(e in results for e in expected))
            self.assertTrue('bar/this' not in results)

    def get_dirs(self, input_path):
        """
        Returns only the type and path from rsync entries.
        """
        return [(e['type'], e['path'])
                for e in rsync.directory_entries(input_path)
                if '.svn' not in e['path']]

    @skipIf(ON_WINDOWS, 'rsync is not available on windows')
    def test_fetch_and_parse_directory_no_recurse(self):
        self.maxDiff = None
        inp = self.get_test_loc('rsync/rsync_dir')
        output = rsync.fetch_directory(inp, recurse=False)
        results = self.get_dirs(output)
        expected = [('d', '.'), ('-', 'foo'), ('d', 'bar')]
        self.assertEqual(sorted(expected), sorted(results))

    def test_directory_output_can_be_parsed_on_protocol_30_and_31(self):
        self.maxDiff = None
        input_30 = self.get_test_loc('rsync/rsync_v3.0.9_protocol30.dir')
        input_31 = self.get_test_loc('rsync/rsync_v3.1.0_protocol31.dir')
        self.assertEqual(self.get_dirs(input_30), self.get_dirs(input_31))
