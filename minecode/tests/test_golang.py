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

from packageurl import PackageURL

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.visitors.golang import GodocIndexVisitor
from minecode.visitors.golang import GodocSearchVisitor
from minecode.visitors.golang import parse_package_path
from minecode.mappers.golang import build_golang_package
from minecode.tests import FIXTURES_REGEN


class GoLangVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_GoLangGoDocAPIVisitor(self):
        uri = 'https://api.godoc.org/packages'
        test_loc = self.get_test_loc('golang/packages.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = GodocIndexVisitor(uri)
        expected_loc = self.get_test_loc('golang/packages_expected_uris.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_GodocSearchVisitor(self):
        uri = 'https://api.godoc.org/search?q=github.com/golang'
        test_loc = self.get_test_loc('golang/godoc_search.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = GodocSearchVisitor(uri)
        expected_loc = self.get_test_loc(
            'golang/godoc_search_expected_uris.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_GodocSearchVisitor_with_non_github_urls(self):
        uri = 'https://api.godoc.org/search?q=github.com/golang*'
        test_loc = self.get_test_loc('golang/godoc_search_off_github.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = GodocSearchVisitor(uri)
        expected_loc = self.get_test_loc(
            'golang/godoc_search_off_github_expected_uris.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_parse_package_path(self):
        test_path = 'github.com/lambdasoup/go-netlink/log'
        purl = PackageURL.from_string(
            'pkg:golang/github.com/lambdasoup/go-netlink'
            '?vcs_repository=https://github.com/lambdasoup/go-netlink')
        expected = purl, 'github.com/lambdasoup/go-netlink'
        assert expected == parse_package_path(test_path)


class GoLangMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_golang_package(self):
        purl = 'pkg:golang/github.com/golang/glog?vcs_repository=https://github.com/golang/glog'
        with open(self.get_test_loc('golang/glog.json')) as f:
            package_data = json.load(f)
        package = build_golang_package(package_data, purl)
        package = package.to_dict()
        expected_loc = self.get_test_loc('golang/glog_expected.json')
        self.check_expected_results(
            package, expected_loc, regen=FIXTURES_REGEN)

    def test_build_golang_package_bitbucket(self):
        purl = 'pkg:bitbucket/bitbucket.org/zombiezen/yaml?vcs_repository=https://bitbucket.org/zombiezen/yaml'
        with open(self.get_test_loc('golang/math3.json')) as f:
            package_data = json.load(f)
        package = build_golang_package(package_data, purl)
        package = package.to_dict()
        expected_loc = self.get_test_loc('golang/math3_expected.json')
        self.check_expected_results(
            package, expected_loc, regen=FIXTURES_REGEN)

    def test_build_golang_package_non_well_known(self):
        purl = 'pkg:golang/winterdrache.de/bindings/sdl'
        with open(self.get_test_loc('golang/winter.json')) as f:
            package_data = json.load(f)
        package = build_golang_package(package_data, purl)
        package = package.to_dict()
        expected_loc = self.get_test_loc('golang/winter_expected.json')
        self.check_expected_results(
            package, expected_loc, regen=FIXTURES_REGEN)
