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

from packagedcode.npm import NpmPackageJsonHandler
from packageurl import PackageURL

import packagedb
from minecode.collectors import npm
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class NpmPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def setUp(self):
        super(NpmPriorityQueueTests, self).setUp()
        self.expected_json_loc = self.get_test_loc("npm/lodash_package-expected.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

        self.scan_package = NpmPackageJsonHandler._parse(
            json_data=self.expected_json_contents,
        )

    def test_get_package_json(self, regen=FIXTURES_REGEN):
        json_contents = npm.get_package_json(
            namespace=self.scan_package.namespace,
            name=self.scan_package.name,
            version=self.scan_package.version,
        )
        if regen:
            with open(self.expected_json_loc, "w") as f:
                json.dump(json_contents, f, indent=3, separators=(",", ":"))
        self.assertEqual(self.expected_json_contents, json_contents)

    def test_map_npm_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string(self.scan_package.purl)
        npm.map_npm_package(package_url, ("test_pipeline"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:npm/lodash@4.17.21"
        expected_download_url = "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
