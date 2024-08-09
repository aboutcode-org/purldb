#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os

from django.test import TestCase
from mock import patch

from minecode.utils_test import JsonBasedTesting
from minecode.visitors import gnu
from packagedb.models import Package


class GnuPriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        super(GnuPriorityQueueTests, self).setUp()
        glibc_data_loc = self.get_test_loc("gnu/glibc/index.html")

        with open(glibc_data_loc) as f:
            self.glibc_data_content = f.read()

    @patch("requests.get")
    def test_process_request(self, mock_get):
        mock_get.side_effect = [
            type(
                "Response",
                (),
                {
                    "content": self.glibc_data_content.encode(),
                    "raise_for_status": lambda: None,
                },
            )
        ]

        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl = "pkg:gnu/glibc@2.15"
        error_msg = gnu.process_request(purl)

        self.assertEqual(None, error_msg)
        package_count = Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = Package.objects.first()
        self.assertEqual("glibc", package.name)
        self.assertEqual("2.15", package.version)

        self.assertEqual(
            "https://ftp.gnu.org/pub/gnu/glibc/glibc-2.15.tar.gz",
            package.download_url,
        )
