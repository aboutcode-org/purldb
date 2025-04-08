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
from minecode.collectors import rubygems
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class RubyGemsPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("rubygems/apiv2/rails-8.0.2.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_package_json(self, regen=FIXTURES_REGEN):
        # As certain fields, such as "downloads," "versions_downloads," and
        # "downloads_count," may vary over time, we cannot rely on
        # "assertEqual" for comparison. Instead, we will verify that the
        # response includes some essential data such as "name" and "version"
        # to make sure json data is collected.
        json_contents = rubygems.get_package_json(
            name="rails",
            version="8.0.2",
        )
        self.assertEqual(json_contents["name"], "rails")
        self.assertEqual(json_contents["version"], "8.0.2")

    def test_map_gem_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:gem/rails@8.0.2")
        rubygems.map_gem_package(package_url, ("test_pipeline"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:gem/rails@8.0.2"
        expected_download_url = "https://rubygems.org/gems/rails-8.0.2.gem"
        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
