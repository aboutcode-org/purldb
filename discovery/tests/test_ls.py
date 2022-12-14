#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os

from discovery.utils_test import JsonBasedTesting
from discovery import ls


class ParseDirectoryListingTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')
#    maxDiff = None

    def test_remove_inode_works_with_no_space_at_line_start(self):
        test = '12190083      4 drwxrwxr-x   4 svnwc    svnwc        4096 May  4 15:57 ./perl'
        expected = u'drwxrwxr-x   4 svnwc    svnwc        4096 May  4 15:57 ./perl'
        self.assertEqual(expected, ls.remove_inode(test))

    def test_remove_inode_works_even_with_space_at_line_start(self):
        test = ' 12190083      4 drwxrwxr-x   4 svnwc    svnwc        4096 May  4 15:57 ./perl'
        expected = u'drwxrwxr-x   4 svnwc    svnwc        4096 May  4 15:57 ./perl'
        self.assertEqual(expected, ls.remove_inode(test))

    def check_listing(self, test_file, expected_file, from_find=True, regen=False):
        test_file = self.get_test_loc(test_file)
        test_text = open(test_file).read()
        results = list(ls.parse_directory_listing(test_text, from_find=from_find))
        for r in results:
            if r.date:
                # we replace the year in YYYY-MM-DD by **** to avoid date-
                # sensitive test failures
                r.date = r.date[0:7]
        results.sort()
        results = [r.to_dict() for r in results]
        expected_file = self.get_test_loc(expected_file)
        self.check_expected_results(results, expected_file, regen=regen)

    def test_parse_listing_from_findls(self):
        test_file = 'directories/find-ls'
        expected_file = 'directories/find-ls-expected.json'
        self.check_listing(test_file, expected_file, from_find=True, regen=False)

    def test_parse_listing_from_findls_from_apache_does_not_fail_on_first_line(self):
        test_file = 'directories/find-ls-apache-start'
        expected_file = 'directories/find-ls-apache-start-expected.json'
        self.check_listing(test_file, expected_file, from_find=True, regen=False)

    def test_parse_listing_from_lslr(self):
        test_file = 'directories/ls-lr'
        expected_file = 'directories/ls-lr-expected.json'
        self.check_listing(test_file, expected_file, from_find=False, regen=False)

    def test_parse_listing_from_lslr_at_ubuntu(self):
        test_file = 'directories/ls-lr-ubuntu'
        expected_file = 'directories/ls-lr-ubuntu-expected.json'
        self.maxDiff = None
        self.check_listing(test_file, expected_file, from_find=False, regen=False)
