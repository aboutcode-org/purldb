# -*- coding: utf-8 -*-
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
from minecode.visitors import URI
from minecode.visitors import googlecode


class GoogleNewAPIVisitorsTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_google_download_zip_visitor(self):
        uri = 'https://storage.googleapis.com/google-code-archive/google-code-archive.txt.zip'
        test_loc = self.get_test_loc('googlecode/google-code-archive.txt.zip')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = googlecode.GooglecodeArchiveVisitor(uri)
        expected_loc = self.get_test_loc('googlecode/expected_google-code-archive.txt.zip.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_google_projectpages(self):
        uri = 'https://code.google.com/archive/search?q=domain:code.google.com'
        test_loc = self.get_test_loc('googlecode/v2_api/GoogleCodeProjectHosting.htm')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = googlecode.GoogleDownloadsPageJsonVisitor(uri)
        expected_loc = self.get_test_loc('googlecode/v2_api/expected_googleprojects.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_google_projectpage2(self):
        uri = 'https://code.google.com/archive/search?q=domain:code.google.com&page=2'
        test_loc = self.get_test_loc('googlecode/v2_api/GoogleCodeProjectHosting_page2.htm')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = googlecode.GoogleDownloadsPageJsonVisitor(uri)
        expected_loc = self.get_test_loc('googlecode/v2_api/expected_googleproject_page2.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_google_download_json(self):
        uri = 'https://storage.googleapis.com/google-code-archive/v2/code.google.com/hg4j/project.json'
        test_loc = self.get_test_loc('googlecode/v2_api/project.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = googlecode.GoogleProjectJsonVisitor(uri)
        self.assertEqual([URI(uri=u'https://storage.googleapis.com/google-code-archive/v2/code.google.com/hg4j/downloads-page-1.json')], list(uris))

    def test_visit_google_json(self):
        uri = 'https://storage.googleapis.com/google-code-archive/v2/code.google.com/hg4j/downloads-page-1.json'
        test_loc = self.get_test_loc('googlecode/v2_api/downloads-page-1.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = googlecode.GoogleDownloadsPageJsonVisitor(uri)
        expected_loc = self.get_test_loc('googlecode/v2_api/hg4j_download_expected.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_googleapi_project_json(self):
        uri = 'https://www.googleapis.com/storage/v1/b/google-code-archive/o/v2%2Fapache-extras.org%2F124799961-qian%2Fproject.json?alt=media'
        test_loc = self.get_test_loc('googlecode/v2_apache-extras.org_124799961-qian_project.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = googlecode.GoogleDownloadsPageJsonVisitor(uri)
        expected_loc = self.get_test_loc('googlecode/expected_v2_apache-extras.org_124799961-qian_project2.json')
        self.check_expected_results(data, expected_loc)


class GoogleNewAPIMappersTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages_from_v2_projects_json(self):
        with open(self.get_test_loc('googlecode/v2_api/project.json')) as projectsjson_meta:
            metadata = json.load(projectsjson_meta)
        packages = mappers.googlecode.build_packages_from_projectsjson_v2(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('googlecode/v2_api/package_expected_project.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages_from_v1_projects_json(self):
        with open(self.get_test_loc('googlecode/v2_apache-extras.org_124799961-qian_project.json')) as projectsjson_meta:
            metadata = json.load(projectsjson_meta)
        packages = mappers.googlecode.build_packages_from_projectsjson_v1(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('googlecode/mapper_expected_v2_apache-extras.org_124799961-qian_project.json')
        self.check_expected_results(packages, expected_loc, regen=False)
