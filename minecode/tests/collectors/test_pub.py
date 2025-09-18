#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from django.test import TestCase as DjangoTestCase
from packageurl import PackageURL

import packagedb
from minecode.collectors import pub
from minecode.utils_test import JsonBasedTesting


class PubPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("pub/flutter.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_pub_package_json(self):
        """
        Verify get_pub_package_json() returns expected keys for a pub package.
        """
        json_contents = pub.get_pub_package_json(name="flutter")
        self.assertIn("name", json_contents)
        self.assertEqual("flutter", json_contents["name"])
        self.assertIn("versions", json_contents)

    def test_map_pub_package(self):
        """
        Verify map_pub_package() creates a Package in the DB with correct PURL
        and download URL.
        """
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)

        package_url = PackageURL.from_string("pkg:pub/flutter@0.0.1")
        pub.map_pub_package(package_url, ("test_pipeline",))

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:pub/flutter@0.0.1"
        expected_download_url = "https://pub.dev/packages/flutter/versions/0.0.1.tar.gz"

        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
