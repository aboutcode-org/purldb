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
from minecode.collectors import cargo
from minecode.utils_test import JsonBasedTesting


class CargoPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("cargo/sam.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)

    def test_get_package_json(self):
        # As certain fields, such as "downloads," "recent_downloads," and
        # "num_versions," may vary over time when executing
        # "cargo.get_package_json(name="sam")", we cannot rely on
        # "assertEqual" for comparison. Instead, we will verify that the
        # response includes four primary components: crate, version,
        # keywords, and categories, and the the "id" under crate is "sam"
        expected_list = ["crate", "versions", "keywords", "categories"]
        json_contents = cargo.get_package_json(name="sam")
        keys = json_contents.keys()
        self.assertListEqual(list(keys), expected_list)
        self.assertEqual(json_contents["crate"]["id"], "sam")

    def test_map_cargo_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:cargo/sam@0.3.1")
        cargo.map_cargo_package(package_url, ("test_pipeline"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:cargo/sam@0.3.1"
        expected_download_url = "https://static.crates.io/crates/sam/sam-0.3.1.crate"
        self.assertEqual(expected_purl_str, package.purl)
        self.assertEqual(expected_download_url, package.download_url)
