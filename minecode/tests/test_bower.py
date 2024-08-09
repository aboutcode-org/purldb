#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import json
import os

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.visitors import bower
from minecode.tests import FIXTURES_REGEN
from minecode import mappers


class BowerVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_findls_file(self):
        uri = 'https://registry.bower.io/packages'
        test_loc = self.get_test_loc('bower/packages.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = bower.BowerTopJsonVisitor(uri)
        expected_loc = self.get_test_loc('bower/packages_expected_uris.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_bower_json_file(self):
        uri = 'https://coding.net/u/QiaoButang/p/jquery.easing-qbt/git/raw/master/bower.json'
        test_loc = self.get_test_loc('bower/example1_bower.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = bower.BowerJsonVisitor(uri)
        result = json.loads(data, object_pairs_hook=OrderedDict)
        expected_loc = self.get_test_loc('bower/expected_example1_bower.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)


class BowerMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages_metafile_from_bowerjson1(self):
        with open(self.get_test_loc('bower/28msec_bower.json')) as bower_metadata:
            metadata = bower_metadata.read()
        result = mappers.bower.build_packages_from_jsonfile(
            metadata, 'https://raw.githubusercontent.com/28msec/28.io-angularjs/master/bower.json', 'pkg:bower/1140-grid')
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc('bower/expected_28msec_bower.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_metafile_from_bowerjson2(self):
        with open(self.get_test_loc('bower/example1_bower.json')) as bower_metadata:
            metadata = bower_metadata.read()
        result = mappers.bower.build_packages_from_jsonfile(
            metadata, 'https://coding.net/u/QiaoButang/p/jquery.easing-qbt/git/raw/master/bower.json', 'pkg:bower/1140-grid')
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc('bower/expected_mapper_example1_bower.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)
