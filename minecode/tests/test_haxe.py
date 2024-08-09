#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import mappers
from minecode.visitors import haxe
from minecode.tests import FIXTURES_REGEN


class HaxeVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_haxe_projects(self):
        uri = 'https://lib.haxe.org/all'
        test_loc = self.get_test_loc('haxe/all_haxelibs.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = haxe.HaxeProjectsVisitor(uri)
        expected_loc = self.get_test_loc('haxe/all_haxelibs.html-expected')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_haxe_versions(self):
        uri = 'https://lib.haxe.org/p/openfl/versions'
        test_loc = self.get_test_loc('haxe/all_versions_openfl.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = haxe.HaxeVersionsVisitor(uri)
        expected_loc = self.get_test_loc(
            'haxe/all_versions_openfl.html-expected')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_haxe_package_json(self):
        uri = 'https://lib.haxe.org/p/openfl/8.5.1/raw-files/openfl/package.json'
        test_loc = self.get_test_loc('haxe/openfl-8.5.1-package.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = haxe.HaxePackageJsonVisitor(uri)
        expected_loc = self.get_test_loc(
            'haxe/openfl-8.5.1-package.json-expected')
        self.check_expected_results(data, expected_loc, regen=FIXTURES_REGEN)


class HaxeMappersTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_project_package_json(self):
        with open(self.get_test_loc('haxe/project_package.json')) as projectsjson_meta:
            metadata = json.load(projectsjson_meta)
        packages = mappers.haxe.build_packages_with_json(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('haxe/project_package.json-expected')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)
