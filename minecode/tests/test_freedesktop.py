#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import mappers
from minecode.visitors import freedesktop


class FreedesktopTest(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')


class FreedesktopVistorTest(FreedesktopTest):

    def test_visit_software_html_page(self):
        uri = 'https://www.freedesktop.org/wiki/Software'
        test_loc = self.get_test_loc('freedesktop/Software.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = freedesktop.FreedesktopHTMLVisitor(uri)
        expected_loc = self.get_test_loc('freedesktop/freedesktop_software_expected')
        self.check_expected_uris(uris, expected_loc)


class FreedesktopMapperTest(FreedesktopTest):

    def test_map_software_html_page_hal(self):
        with open(self.get_test_loc('freedesktop/hal.html')) as freedesktop_metadata:
            metadata = freedesktop_metadata.read()
        packages = mappers.freedesktop.build_packages(
            metadata,
            'https://www.freedesktop.org/wiki/Software/hal',
            purl='pkg:freedesktop/hal')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('freedesktop/hal_project_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_map_software_html_page_libinput(self):
        with open(self.get_test_loc('freedesktop/libinput.html')) as freedesktop_metadata:
            metadata = freedesktop_metadata.read()
        packages = mappers.freedesktop.build_packages(
            metadata,
            'https://www.freedesktop.org/wiki/Software/libinput/',
            purl='pkg:freedesktop/libinput')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('freedesktop/libinput_project_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)
