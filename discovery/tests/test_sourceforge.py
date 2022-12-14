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

from mock import patch

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting

from discovery import mappers
from discovery.visitors import sourceforge


class SourceforgeVisitorsTest(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_sf_sitemap_index_new(self):
        uri = 'http://sourceforge.net/sitemap.xml'
        test_loc = self.get_test_loc('sourceforge/sitemap.xml')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, error = sourceforge.SourceforgeSitemapIndexVisitor(uri)

        expected_loc = self.get_test_loc('sourceforge/expected_sf_sitemap_new.json')
        self.check_expected_uris(uris, expected_loc)
        self.assertIsNone(error)

    def test_visit_sf_sitemap_page_new(self):
        uri = 'http://sourceforge.net/sitemap-1.xml'
        test_loc = self.get_test_loc('sourceforge/sitemap-1.xml')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, error = sourceforge.SourceforgeSitemapPageVisitor(uri)

        expected_loc = self.get_test_loc('sourceforge/expected_sf_sitemap_page_new.json')
        self.check_expected_uris(uris, expected_loc)
        self.assertIsNone(error)

    def test_visit_sf_sitemap_page6(self):
        uri = 'https://sourceforge.net/sitemap-6.xml'
        test_loc = self.get_test_loc('sourceforge/sitemap-6.xml')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, error = sourceforge.SourceforgeSitemapPageVisitor(uri)

        expected_loc = self.get_test_loc('sourceforge/expected_sitemap-6.json')
        self.check_expected_uris(uris, expected_loc)
        self.assertIsNone(error)

    def test_visit_sf_project_json_api_new(self):
        uri = 'https://sourceforge.net/api/project/name/netwiki/json'
        test_loc = self.get_test_loc('sourceforge/netwiki.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, error = sourceforge.SourceforgeProjectJsonVisitor(uri)

        expected_loc = self.get_test_loc('sourceforge/expected_netwiki.json')
        self.check_expected_results(data, expected_loc)
        self.assertIsNone(error)


class SourceforgeMappersTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('sourceforge/odanur.json')) as sourceforge_metadata:
            metadata = json.load(sourceforge_metadata)
        packages = mappers.sourceforge.build_packages_from_metafile(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('sourceforge/mapper_odanur_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages2(self):
        with open(self.get_test_loc('sourceforge/openstunts.json')) as sourceforge_metadata:
            metadata = json.load(sourceforge_metadata)
        packages = mappers.sourceforge.build_packages_from_metafile(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('sourceforge/mapper_openstunts_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages3(self):
        with open(self.get_test_loc('sourceforge/monoql.json')) as sourceforge_metadata:
            metadata = json.load(sourceforge_metadata)
        packages = mappers.sourceforge.build_packages_from_metafile(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('sourceforge/mapper_omonoql_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages4(self):
        with open(self.get_test_loc('sourceforge/niftyphp.json')) as sourceforge_metadata:
            metadata = json.load(sourceforge_metadata)
        packages = mappers.sourceforge.build_packages_from_metafile(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('sourceforge/mapper_niftyphp_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)
