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
from packageurl import PackageURL
import packagedb
from minecode.collectors import conda
from minecode.utils_test import JsonBasedTesting


class CondaPriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.package_url = PackageURL.from_string(
            "pkg:conda/numpy@1.11.3?subdir=linux-64&build=py27h1b885b7_8&type=tar.bz2"
        )
        self.download_url = (
            "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.11.3-py27h1b885b7_8.tar.bz2"
        )

    def test_map_conda_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        conda.map_conda_package(self.package_url, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 1)
        package = packagedb.models.Package.objects.all().first()
        expected_conda_download_url = self.download_url

        self.assertEqual(package.purl, str(self.package_url))
        self.assertEqual(package.download_url, expected_conda_download_url)
