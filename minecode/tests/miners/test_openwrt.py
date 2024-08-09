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
from unittest.case import expectedFailure

from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import miners
from minecode.miners import openwrt
from minecode.tests import FIXTURES_REGEN


class OpenWRTVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles')

    def test_visit_openwrt_download_pages(self):
        uri = 'https://downloads.openwrt.org/chaos_calmer/15.05/'
        test_loc = self.get_test_loc(
            'openwrt/Index_of_chaos_calmer_15.05_.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = openwrt.OpenWrtDownloadPagesVisitor(uri)
        expected_loc = self.get_test_loc('openwrt/chaos_calmer_15.05_expected')
        self.check_expected_uris(uris, expected_loc)

    def test_visitor_openwrt_download_pages2(self):
        uri = 'https://downloads.openwrt.org/chaos_calmer/15.05/adm5120/rb1xx/packages/base/'
        test_loc = self.get_test_loc(
            'openwrt/Index_of_chaos_calmer_15.05_adm5120_rb1xx_packages_base_.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = openwrt.OpenWrtDownloadPagesVisitor(uri)
        expected_loc = self.get_test_loc(
            'openwrt/chaos_calmer_15.05_expected_2')
        self.check_expected_uris(uris, expected_loc)

    @expectedFailure
    def test_visitor_openwrt_packages_gz(self):
        uri = 'https://downloads.openwrt.org/chaos_calmer/15.05/adm5120/rb1xx/packages/base/Packages.gz'
        test_loc = self.get_test_loc('openwrt/Packages.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = openwrt.OpenWrtPackageIndexVisitor(uri)

        expected_loc = self.get_test_loc('openwrt/Packages_gz_expected')
        self.check_expected_uris(uris, expected_loc)

    @expectedFailure
    def test_visitor_openwrt_ipk(self):
        uri = 'https://downloads.openwrt.org/chaos_calmer/15.05/adm5120/rb1xx/packages/base/6to4_12-2_all.ipk'
        test_loc = self.get_test_loc('openwrt/6to4_12-2_all.ipk')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = openwrt.OpenWrtPackageIndexVisitor(uri)

        result = json.loads(data)
        json_file = self.get_test_loc('openwrt/6to4_12-2_all_ipk_expected')
        self.check_expected_results(result, json_file, regen=FIXTURES_REGEN)

    @expectedFailure
    def test_visitor_openwrt_ipk2(self):
        uri = 'https://downloads.openwrt.org/kamikaze/7.09/brcm-2.4/packages/wpa-cli_0.5.7-1_mipsel.ipk'
        test_loc = self.get_test_loc('openwrt/wpa-cli_0.5.7-1_mipsel.ipk')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = openwrt.OpenWrtPackageIndexVisitor(uri)

        result = json.loads(data)
        json_file = self.get_test_loc(
            'openwrt/wpa-cli_0.5.7-1_mipsel.ipk_expected')
        self.check_expected_results(result, json_file)


class OpenWRTMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles')

    @expectedFailure
    def test_build_packages_1(self):
        with open(self.get_test_loc('openwrt/6to4_12-2_all_ipk_expected')) as openwrt_ipk_meta:
            metadata = json.load(openwrt_ipk_meta)
        packages = miners.openwrt.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'openwrt/6to4_12-2_all_ipk_expected_mapper.json')
        self.check_expected_results(packages, expected_loc)

    @expectedFailure
    def test_build_packages_2(self):
        with open(self.get_test_loc('openwrt/wpa-cli_0.5.7-1_mipsel.ipk_expected')) as openwrt_ipk_meta:
            metadata = json.load(openwrt_ipk_meta)
        packages = miners.openwrt.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'openwrt/wpa-cli_0.5.7-1_mipsel.ipk_expected_mapper.json')
        self.check_expected_results(packages, expected_loc)
