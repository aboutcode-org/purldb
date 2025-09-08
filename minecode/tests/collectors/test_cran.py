#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from django.test import TestCase as DjangoTestCase
from packageurl import PackageURL

import packagedb
from minecode.collectors import cran
from minecode.utils_test import JsonBasedTesting


class CranPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("cran/dplyr.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_package_json(self):
        """
        Verify get_cran_package_json() returns expected keys for CRAN package.
        """
        json_contents = cran.get_cran_package_json(name="dplyr")
        self.assertIn("versions", json_contents)
        self.assertIn("dplyr", json_contents.get("Package", "dplyr"))

    def test_map_cran_package(self):
        """
        Verify map_cran_package() creates a Package in the DB with correct PURL
        and download URL.
        """
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)

        package_url = PackageURL.from_string("pkg:cran/dplyr@1.1.0")
        cran.map_cran_package(package_url, ("test_pipeline",))

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:cran/dplyr@1.1.0"
        expected_download_url = "https://cran.r-project.org/src/contrib/dplyr_1.1.0.tar.gz"

        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
