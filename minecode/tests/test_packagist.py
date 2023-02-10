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

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import mappers
from minecode.visitors import packagist


class PackagistVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_packagistlist(self):
        uri = 'https://packagist.org/packages/list.json'
        test_loc = self.get_test_loc('packagist/list.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = packagist.PackagistListVisitor(uri)
        expected_loc = self.get_test_loc('packagist/packagist_list_expected')
        self.check_expected_uris(uris, expected_loc)


class TestPackagistMap(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('packagist/00f100_cakephp-opauth.json')) as packagist_package:
            metadata = json.load(packagist_package)
        packages = mappers.packagist.build_packages_with_json(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('packagist/packaglist_00f100_cakephp-opauth_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)
