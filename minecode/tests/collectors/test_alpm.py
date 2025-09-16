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
from minecode.collectors import alpm
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class AlpmPriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def setUp(self):
        super().setUp()
        self.package_url1 = PackageURL.from_string("pkg:alpm/bemenu-ncurses@0.6.13-1?arch=x86_64")
        self.download_url1 = "https://archive.archlinux.org/packages/b/bemenu-ncurses/bemenu-ncurses-0.6.13-1-x86_64.pkg.tar.zst"
        self.extracted_location1 = self.get_test_loc("alpm/bemenu-ncurses/")

    def test_build_packages(self):
        packages = alpm.build_packages(
            self.extracted_location1, self.download_url1, self.package_url1
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("alpm/bemenu_ncurses_expected.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_map_alpm_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        alpm.map_alpm_package(self.package_url1, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 1)
        package = packagedb.models.Package.objects.all().first()
        expected_bemenu_download_url = self.download_url1

        self.assertEqual(package.purl, str(self.package_url1))
        self.assertEqual(package.download_url, expected_bemenu_download_url)
