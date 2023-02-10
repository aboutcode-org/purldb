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
import re

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import mappers
from minecode.visitors import nuget


class NugetVisitorsTest(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_NugetQueryVisitor(self):
        uri = 'https://api-v2v3search-0.nuget.org/query'
        test_loc = self.get_test_loc('nuget/query.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = nuget.NugetQueryVisitor(uri)
        expected_loc = self.get_test_loc('nuget/nuget_query_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_PackagesPageVisitor(self):
        uri = 'https://api-v2v3search-0.nuget.org/query?skip=0'
        test_loc = self.get_test_loc('nuget/query_search.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = nuget.PackagesPageVisitor(uri)
        expected_loc = self.get_test_loc('nuget/nuget_page_json_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_NugetAPIJsonVisitor(self):
        uri = 'https://api.nuget.org/v3/registration1/entityframework/6.1.3.json'
        test_loc = self.get_test_loc('nuget/entityframework.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = nuget.NugetAPIJsonVisitor(uri)
        expected_loc = self.get_test_loc('nuget/nuget_downlloadvisitor_json_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_NugetHTMLPageVisitor(self):
        uri = 'https://www.nuget.org/packages?page=1'
        test_loc = self.get_test_loc('nuget/packages.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = nuget.NugetHTMLPageVisitor(uri)
        expected_loc = self.get_test_loc('nuget/packages.html.expected.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_NugetHTMLPackageVisitor(self):
        uri = 'https://www.nuget.org/packages/log4net'
        test_loc = self.get_test_loc('nuget/log4net.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _errors = nuget.NugetHTMLPackageVisitor(uri)
        self.assertTrue(b'Apache-2.0 License ' in data)
        self.assertTrue(b'log4net is a tool to help the programmer' in data)


class TestNugetMap(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('nuget/entityframework2.json')) as nuget_metadata:
            metadata = json.load(nuget_metadata)
        packages = mappers.nuget.build_packages_with_json(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('nuget/nuget_mapper_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_regex_1(self):
        regex = re.compile(r'^https://api.nuget.org/packages/.*\.nupkg$')
        result = re.match(regex, 'https://api.nuget.org/packages/entityframework.4.3.1.nupkg')
        self.assertTrue(result)

    def test_regex_2(self):
        regex = re.compile(r'^https://api.nuget.org/v3/catalog.+\.json$')
        result = re.match(regex, 'https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json')
        self.assertTrue(result)

    def test_build_packages_from_html(self):
        uri = 'https://www.nuget.org/packages/log4net'
        test_loc = self.get_test_loc('nuget/log4net.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _errors = nuget.NugetHTMLPackageVisitor(uri)
            packages = mappers.nuget.build_packages_from_html(data, uri,)
            packages = [p.to_dict() for p in packages]
            expected_loc = self.get_test_loc('nuget/nuget_mapper_log4net_expected.json')
            self.check_expected_results(packages, expected_loc, regen=False)
