#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import re

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.visitors import gstreamer
from minecode import mappers


class GstreamerVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_gstreamer_source_root(self):
        uri = 'https://gstreamer.freedesktop.org/src/'
        test_loc = self.get_test_loc('gstreamer/src_root.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = gstreamer.GstreamerHTMLVisitor(uri)
        expected_loc = self.get_test_loc('gstreamer/src_root.html-expected')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_Gstreamer_subpath_contains_file_resources(self):
        uri = 'https://gstreamer.freedesktop.org/src/gst-openmax/pre/'
        test_loc = self.get_test_loc('gstreamer/src_gst-openmax_pre.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = gstreamer.GstreamerHTMLVisitor(uri)
        expected_loc = self.get_test_loc('gstreamer/src_gst-openmax_pre.html-expected')
        self.check_expected_uris(uris, expected_loc)


class GstreamerMappersTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_package_mapper_regex(self):
        regex = re.compile(r'^https://gstreamer.freedesktop.org/src/([\w\-\.]+/)*[\w\-\.]+[.tar\.bz2|\.sha1sum|\.md5|\.gz|\.tar\.xz|\.asc]$')
        result = re.match(regex, 'https://gstreamer.freedesktop.org/src/gst-openmax/pre/gst-openmax-0.10.0.2.tar.bz2')
        self.assertTrue(result)

    def test_build_package_from_url(self):
        packages = mappers.gstreamer.build_package_from_url('https://gstreamer.freedesktop.org/src/gst-openmax/pre/gst-openmax-0.10.0.2.tar.bz2')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('gstreamer/mapper_build_from_url-expected')
        self.check_expected_results(packages, expected_loc, regen=False)
