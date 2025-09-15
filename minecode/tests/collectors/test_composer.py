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
from minecode.collectors import composer
from minecode.utils_test import JsonBasedTesting


class ComposerPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        # Sample Packagist metadata for laravel/laravel
        self.expected_json_loc = self.get_test_loc("composer/laravel-laravel.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_package_json(self):
        """
        Verify that get_composer_package_json() fetches metadata and contains
        the expected "packages" structure, with laravel/laravel present.
        """
        json_contents = composer.get_composer_package_json(name="laravel/laravel")
        self.assertIn("packages", json_contents)
        self.assertIn("laravel/laravel", json_contents["packages"])

    def test_map_composer_package(self):
        """
        Verify that map_composer_package() creates a Package in the DB with the
        correct PURL and download URL from Packagist metadata.
        """
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)

        package_url = PackageURL.from_string("pkg:composer/laravel/laravel@v11.0.0")
        composer.map_composer_package(package_url, ("test_pipeline",))

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:composer/laravel/laravel@v11.0.0"

        # dist.url from Packagist metadata is expected to be something like:
        # https://api.github.com/repos/laravel/laravel/zipball/<commit>
        self.assertEqual(expected_purl_str, package.purl)
        self.assertTrue(package.download_url.startswith("https://"))
        self.assertIn("laravel", package.download_url.lower())
