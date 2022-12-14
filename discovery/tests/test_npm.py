#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import codecs
import json
import os
import re

from mock import Mock
from mock import patch

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting

from discovery import mappers
from discovery import route
from discovery.models import ResourceURI
from discovery.visitors import npm


class TestNPMVisit(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    # FIXME: use smaller test files
    def test_NpmRegistryVisitor(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since=2300000'
        test_loc = self.get_test_loc('npm/replicate_doc1.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _errors = npm.NpmRegistryVisitor(uri)
        # this is a non-persistent visitor, lets make sure we dont return any data
        assert not data
        expected_loc = self.get_test_loc('npm/expected_doclimit_visitor.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_NpmRegistryVisitor_OverLimit(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since=2300000'
        test_loc = self.get_test_loc('npm/over_limit.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = npm.NpmRegistryVisitor(uri)
        expected_loc = self.get_test_loc('npm/expected_over_limit.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_NpmRegistryVisitor_1000records(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since=77777'
        test_loc = self.get_test_loc('npm/1000_records.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = npm.NpmRegistryVisitor(uri)
        expected_loc = self.get_test_loc('npm/expected_1000_records.json')
        self.check_expected_uris(uris, expected_loc, regen=False)


class TestNPMMapper(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('npm/0flux.json')) as npm_metadata:
            metadata = json.load(npm_metadata)
        packages = mappers.npm.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/0flux_npm_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package2(self):
        with open(self.get_test_loc('npm/2112.json')) as npm_metadata:
            metadata = json.load(npm_metadata)
        packages = mappers.npm.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/npm_2112_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package3(self):
        with open(self.get_test_loc('npm/microdata.json')) as npm_metadata:
            metadata = json.load(npm_metadata)
        packages = mappers.npm.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/microdata-node_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package_with_visitor_data(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since=77777'
        test_loc = self.get_test_loc('npm/1000_records.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = npm.NpmRegistryVisitor(uri)
        uris_list = list(uris)
        assert len(uris_list) == 1001
        # Randomly pick a record from 0-1000
        metadata = uris_list[29].data
        packages = mappers.npm.build_packages(json.loads(metadata))
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/29_record_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

        # Randomly pick a record from 0-1000
        metadata = uris_list[554].data
        packages = mappers.npm.build_packages(json.loads(metadata))
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/554_record_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package_with_ticket_439(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=10&since=7333426'
        test_loc = self.get_test_loc('npm/ticket_439.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = npm.NpmRegistryVisitor(uri)
        uris_list = list(uris)
        assert len(uris_list) == 11
        # Pickup the first one,  since it's the one which is the problem package "angular2-autosize"
        # The zero element in json is the url for next visitor use, and data is empty and the url is
        metadata = uris_list[1].data
        packages = mappers.npm.build_packages(json.loads(metadata))
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/expected_ticket_439.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package_verify_ticket_440(self):
        uri = 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=10&since=7632607'
        test_loc = self.get_test_loc('npm/ticket_440_records.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = npm.NpmRegistryVisitor(uri)
        uris_list = list(uris)
        assert len(uris_list) == 11
        # Pickup the index one instead of zero,  since it's the one which is the problem package "npm-research", https://registry.npmjs.org/npm-research,
        # The zero element in json is the url for next visitor use only
        metadata = uris_list[1].data
        packages = mappers.npm.build_packages(json.loads(metadata))
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/expected_ticket_440.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_npm_mapper(self):
        test_uri = 'https://registry.npmjs.org/angular-compare-validator'
        router = route.Router()
        router.append(test_uri, mappers.npm.NpmPackageMapper)
        test_loc = self.get_test_loc('npm/mapper/index.json')
        with open(test_loc, 'rb') as test_file:
            test_data = test_file.read().decode('utf-8')

        test_res_uri = ResourceURI(uri=test_uri, data=test_data)
        packages = mappers.npm.NpmPackageMapper(test_uri, test_res_uri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/mapper/index.expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_package_for_jsonp_filter(self):
        with open(self.get_test_loc('npm/jsonp-filter.json')) as npm_metadata:
            metadata = json.load(npm_metadata)
        packages = mappers.npm.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('npm/jsonp-filter-expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_regex_npm_mapper(self):
        regex = re.compile(r'^https://registry.npmjs.org/[^\/]+$')
        result = re.match(regex, 'https://registry.npmjs.org/react-mobile-navigation-modal')
        self.assertTrue(result)
