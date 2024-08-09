#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import unittest

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.visitors import gitlab
from minecode.tests import FIXTURES_REGEN
from minecode import mappers


class GitlabTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')


class GitlabVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    @unittest.skip('The test is to test fetching remotely through http connection')
    def test_visit_api_header_getheaders(self):
        uri = 'https://gitlab.com/api/v4/projects'
        uris, _, _ = gitlab.GitlabAPIHeaderVisitor(uri)
        expected_loc = self.get_test_loc('gitlab/expected_projects.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_metacpan_api_projects(self):
        uri = 'https://gitlab.com/api/v4/projects?page=1&per_page=70&statistics=true'
        test_loc = self.get_test_loc('gitlab/projects_visitor.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = gitlab.GitlabAPIVisitor(uri)
        expected_loc = self.get_test_loc(
            'gitlab/expected_projects_visitor.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)


class GitlabMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_map_software_html_page_hal(self):
        with open(self.get_test_loc('gitlab/microservice-express-mongo.json')) as gitlab_json:
            metadata = gitlab_json.read()
        packages = mappers.gitlab.build_packages_from_json(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'gitlab/microservice-express-mongo_expected.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)
