#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from django.test import TestCase
from packageurl import PackageURL
import packagedb
from minecode.collectors import swift
from minecode.utils_test import JsonBasedTesting


class SwiftPriorityQueueTests(JsonBasedTesting, TestCase):
    def setUp(self):
        super().setUp()
        self.package_url = PackageURL.from_string("pkg:swift/github.com/Alamofire/Alamofire@5.4.3")
        self.download_url = "https://github.com/Alamofire/Alamofire/archive/5.4.3.zip"

    def test_map_swift_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        swift.map_swift_package(self.package_url, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 1)
        package = packagedb.models.Package.objects.all().first()
        expected_download_url = self.download_url

        self.assertEqual(package.purl, str(self.package_url))
        self.assertEqual(package.download_url, expected_download_url)
