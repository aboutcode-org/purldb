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
from minecode.collectors import cpan
from minecode.utils_test import JsonBasedTesting


class CpanPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("cpan/Mojolicious-9.22.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_cpan_release_json(self):
        """
        Verify get_cpan_release_json() returns expected keys for CPAN distribution.
        """
        json_contents = cpan.get_cpan_release_json(distribution="Mojolicious", version="9.22")
        self.assertIn("distribution", json_contents)
        self.assertEqual("Mojolicious", json_contents["distribution"])
        self.assertEqual("9.22", json_contents["version"])

    def test_map_cpan_package(self):
        """
        Verify map_cpan_package() creates a Package in the DB with correct PURL
        and download URL.
        """
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)

        package_url = PackageURL.from_string("pkg:cpan/Mojolicious@9.22")
        cpan.map_cpan_package(package_url, ("test_pipeline",))

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:cpan/Mojolicious@9.22"
        expected_download_url = (
            "https://cpan.metacpan.org/authors/id/S/SR/SRI/Mojolicious-9.22.tar.gz"
        )

        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
