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
import unittest

from mock import Mock
from mock import patch
import requests

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import mappers
from minecode.visitors import URI
from minecode.visitors import eclipse


class EclipseVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_eclipse_projects(self):
        uri = 'https://projects.eclipse.org/list-of-projects'
        test_loc = self.get_test_loc('eclipse/projects.eclipse.org.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = eclipse.EclipseProjectVisitors(uri)
        expected_loc = self.get_test_loc('eclipse/eclipse_projects_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_eclipse_project(self):
        uri = 'https://projects.eclipse.org/projects/modeling.m2t.acceleo'
        test_loc = self.get_test_loc('eclipse/Acceleo_projects.eclipse.org.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = eclipse.EclipseSingleProjectVisitor(uri)
        with open(self.get_test_loc('eclipse/acceleo_expected.html'), 'rb') as data_file:
            self.assertEquals(data_file.read(), data)

    def test_visit_eclipse_git_repo(self):
        uri = 'http://git.eclipse.org/c'
        test_loc = self.get_test_loc('eclipse/Eclipse_Git_repositories.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = eclipse.EclipseGitVisitor(uri)
        expected_loc = self.get_test_loc('eclipse/eclipse_git_repos_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_eclipse_packages(self):
        uri = 'http://www.eclipse.org/downloads/packages/all'
        test_loc = self.get_test_loc('eclipse/All_Releases_Packages.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = eclipse.EclipsePackagesVisitor(uri)
        expected_loc = self.get_test_loc('eclipse/eclipse_packages_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_eclipse_package_releases(self):
        uri = 'http://www.eclipse.org/downloads/packages/release/Neon/R'
        test_loc = self.get_test_loc('eclipse/Neon_R.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = eclipse.EclipseReleaseVisitor(uri)
        expected_loc = self.get_test_loc('eclipse/Neon_R-expected.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_eclipse_projects_json(self):
        uri = 'http://projects.eclipse.org/json/projects/all'
        test_loc = self.get_test_loc('eclipse/birt.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _error = eclipse.EclipseProjectsJsonVisitor(uri)

        expected_uris = [
            URI(uri=u'http://projects.eclipse.org/json/project/birt',
                source_uri=u'http://projects.eclipse.org/json/projects/all',
                package_url=u'pkg:eclipse/birt')]
        self.assertEqual(expected_uris, list(uris))

        expected_loc = self.get_test_loc('eclipse/birt-expected.json')
        self.check_expected_results(data, expected_loc, regen=False)

    @unittest.skip('This requires a live internet connection to test requests timeouts')
    def test_visitor_eclipse_projects_json_download_timeout_error(self):
        uri = 'http://projects.eclipse.org/json/projects/all'
        try:
            eclipse.EclipseProjectsJsonVisitor(uri)
        except requests.Timeout:
            self.fail(
                "Time out error happens when download the url, "
                "this should be fixed by increaseing the timeout.")


class TestEclipseMap(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('eclipse/birt.json')) as eclipse_metadata:
            metadata = json.load(eclipse_metadata)
        packages = mappers.eclipse.build_packages_with_json(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('eclipse/eclipse_birt_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_eclipse_html_packages(self):
        with open(self.get_test_loc('eclipse/Acceleo_projects.eclipse.org.html')) as eclipse_metadata:
            metadata = eclipse_metadata.read()
        packages = mappers.eclipse.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('eclipse/Acceleo_projects_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)
