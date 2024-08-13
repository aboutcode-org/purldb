#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os
from unittest.mock import patch

from django.test import TestCase

import saneyaml
from packageurl import PackageURL

import packagedb
from minecode.collectors import conan
from minecode.utils_test import JsonBasedTesting


class ConanPriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def setUp(self):
        super().setUp()
        self.package_url1 = PackageURL.from_string("pkg:conan/zlib@1.3.1")
        zlib_conanfile_loc = self.get_test_loc("conan/zlib/manifest/conanfile.py")
        zlib_conandata_loc = self.get_test_loc("conan/zlib/manifest/conandata.yml")
        zlib_config_loc = self.get_test_loc("conan/zlib/manifest/config.yml")

        with open(zlib_conanfile_loc) as f:
            self.zlib_conanfile_contents = f.read()

        with open(zlib_config_loc) as f:
            self.zlib_config_contents = f.read()

        with open(zlib_conandata_loc) as f:
            self.zlib_conandata_contents = f.read()

        self.zlib_conandata_contents_dict = saneyaml.load(self.zlib_conandata_contents)

    @patch("requests.get")
    def test_get_conan_recipe(self, mock_get):
        mock_get.side_effect = [
            type(
                "Response",
                (),
                {
                    "content": self.zlib_config_contents.encode(),
                    "raise_for_status": lambda: None,
                },
            ),
            type(
                "Response",
                (),
                {
                    "content": self.zlib_conandata_contents.encode(),
                    "raise_for_status": lambda: None,
                },
            ),
            type(
                "Response",
                (),
                {
                    "text": self.zlib_conanfile_contents,
                    "raise_for_status": lambda: None,
                },
            ),
        ]
        result_conanfile, result_conandata = conan.get_conan_recipe(
            self.package_url1.name, self.package_url1.version
        )

        self.assertEqual(result_conanfile, self.zlib_conanfile_contents)
        self.assertEqual(result_conandata, self.zlib_conandata_contents_dict)

    def test_get_download_info(self):
        result_download_url, result_sha256 = conan.get_download_info(
            self.zlib_conandata_contents_dict, self.package_url1.version
        )
        expected_zlib_download_url = "https://zlib.net/fossils/zlib-1.3.1.tar.gz"
        expected_zlib_sha256 = (
            "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"
        )

        self.assertEqual(result_download_url, expected_zlib_download_url)
        self.assertEqual(result_sha256, expected_zlib_sha256)

    @patch("minecode.collectors.conan.get_conan_recipe")
    def test_map_conan_package(self, mock_get_conan_recipe):
        mock_get_conan_recipe.return_value = (
            self.zlib_conanfile_contents,
            self.zlib_conandata_contents_dict,
        )

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        conan.map_conan_package(self.package_url1, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 1)
        package = packagedb.models.Package.objects.all().first()
        expected_zlib_download_url = "https://zlib.net/fossils/zlib-1.3.1.tar.gz"

        self.assertEqual(package.purl, str(self.package_url1))
        self.assertEqual(package.download_url, expected_zlib_download_url)
