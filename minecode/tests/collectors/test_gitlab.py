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

from minecode.collectors import gitlab
from minecode.utils_test import JsonBasedTesting


class GitlabPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_gitlab_get_all_package_version_author(self):
        repo_path = "xx_network%2Fprimitives"
        version_author_list = gitlab.gitlab_get_all_package_version_author(repo_path)
        expected = [
            ("v0.0.5", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.4", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.3", "Benjamin Wenger", "ben@privategrity.com"),
            ("v0.0.2", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.1", "Jonathan Wenger", "jono@elixxir.io"),
            ("v0.0.0", "Sydney Anne Erickson", "sydney@elixxir.io"),
        ]
        for item in version_author_list:
            self.assertIn(item, expected)
