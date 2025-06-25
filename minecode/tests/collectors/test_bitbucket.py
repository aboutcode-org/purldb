#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TestCase as DjangoTestCase

from minecode.collectors import bitbucket
from minecode.utils_test import JsonBasedTesting


class BitbucketPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_bitbucket_get_all_package_version_author(self):
        repo_path = "creachadair/stringset"
        version_author_list = bitbucket.bitbucket_get_all_package_version_author(repo_path)
        expected = [
            ("v0.0.1", "M. J. Fromberger"),
            ("v0.0.10", "M. J. Fromberger"),
            ("v0.0.11", "M. J. Fromberger"),
            ("v0.0.12", "M. J. Fromberger"),
            ("v0.0.13", "M. J. Fromberger"),
            ("v0.0.14", "M. J. Fromberger"),
            ("v0.0.2", "M. J. Fromberger"),
            ("v0.0.3", "M. J. Fromberger"),
            ("v0.0.4", "M. J. Fromberger"),
            ("v0.0.5", "M. J. Fromberger"),
            ("v0.0.6", "M. J. Fromberger"),
            ("v0.0.7", "M. J. Fromberger"),
            ("v0.0.8", "M. J. Fromberger"),
            ("v0.0.9", "M. J. Fromberger"),
        ]
        for item in version_author_list:
            self.assertIn(item, expected)
