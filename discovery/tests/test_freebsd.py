#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os
import yaml

from mock import Mock
from mock import patch

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting

from discovery import mappers
from discovery.visitors import freebsd


class FreeBSDVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_freebsd_seed(self):
        uri = 'https://pkg.freebsd.org'
        test_loc = self.get_test_loc('freebsd/FreeBSD.org.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = freebsd.FreeBSDBaseHTMLVisitors(uri)
        expected_loc = self.get_test_loc('freebsd/FreeBSD.org.html_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_freebsd_subHTML(self):
        uri = 'https://pkg.freebsd.org/FreeBSD:10:i386/release_0/'
        test_loc = self.get_test_loc('freebsd/FreeBSD-10-i386_release_0_.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = freebsd.FreeBSDSubHTMLVisitors(uri)
        expected_loc = self.get_test_loc('freebsd/FreeBSD-10-i386_release_0_.html_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_freebsd_indexvisitor(self):
        uri = 'https://pkg.freebsd.org/FreeBSD:10:i386/release_0/packagesite.txz'
        test_loc = self.get_test_loc('freebsd/packagesite.txz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = freebsd.FreeBSDIndexVisitors(uri)
        expected_loc = self.get_test_loc('freebsd/indexfile_expected')
        self.check_expected_results(data, expected_loc, regen=False)


class FreedesktopMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_map_index_file(self):
        with open(self.get_test_loc('freebsd/mapper_input1')) as freebsd_metadata:
            metadata = freebsd_metadata.read()
        packages = mappers.freebsd.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'freebsd/indexfile_expected_mapper.json')
        self.check_expected_results(packages, expected_loc, regen=False)
