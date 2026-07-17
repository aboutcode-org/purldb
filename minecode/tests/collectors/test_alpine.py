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
from minecode.collectors import alpine
from minecode.utils_test import JsonBasedTesting


class AlpinePriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.package_url = PackageURL.from_string(
            "pkg:apk/ansible@1.6.7-r0?arch=x86&repo=main&alpine_version=v3.0"
        )
        self.download_url = (
            "https://dl-cdn.alpinelinux.org/alpine/v3.0/main/x86/ansible-1.6.7-r0.apk"
        )

    def test_map_alpine_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        alpine.map_apk_package(self.package_url, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 1)
        package = packagedb.models.Package.objects.all().first()
        expected_conda_download_url = self.download_url

        self.assertEqual(package.purl, str(self.package_url))
        self.assertEqual(package.download_url, expected_conda_download_url)
