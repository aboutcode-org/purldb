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
from minecode.collectors import pypi
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class PypiPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("pypi/cage_1.1.4.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_package_json(self, regen=FIXTURES_REGEN):
        json_contents = pypi.get_package_json(
            name="cage",
            version="1.1.4",
        )
        if regen:
            self.expected_json_contents = json_contents
            with open(self.expected_json_loc, "w") as f:
                json.dump(json_contents, f)
        self.assertEqual(self.expected_json_contents, json_contents)

    def test_get_all_package_version(self):
        releases_list = pypi.get_all_package_version("cage")
        expected = ["1.1.2", "1.1.3", "1.1.4"]
        # At the time of creating this test, the CAGE project has three
        # releases. There may be additional releases in the future.
        # Therefore, we will verify that the number of releases is three
        # or greater and that it includes the expected release versions.
        self.assertTrue(len(releases_list) >= 3)
        for version in expected:
            self.assertIn(version, releases_list)

    def test_map_pypi_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:pypi/cage@1.1.4")
        pypi.map_pypi_package(package_url, ("test_pipeline"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:pypi/cage@1.1.4"
        expected_download_url = "http://www.alcyone.com/software/cage/cage-latest.tar.gz"
        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
        self.assertEqual(
            packagedb.models.PackageContentType.SOURCE_ARCHIVE, package.package_content
        )
