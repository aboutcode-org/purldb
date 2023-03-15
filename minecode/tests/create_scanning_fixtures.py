# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TestCase

from minecode.models import ScannableURI
from packagedb.models import Package
from minecode.management import scanning
from minecode.utils_test import JsonBasedTesting
from minecode.management.commands.request_scans import Command as RequestScansCommand
from minecode.management.commands.process_scans import Command as ProcessScansCommand


class ScanCodeIOAPIHelperFunctionTest(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1, _ = Package.objects.get_or_create(
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            type='maven',
            namespace='',
            name='wagon-api',
            version='20040705.181715',
        )
        self.scannable_uri1, _ = ScannableURI.objects.get_or_create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            package=self.package1
        )

    def generate_api_responses(self):
        scan_request_response_loc = self.get_test_loc('scancodeio/scan_request_response.json')
        RequestScansCommand.process_scan(
            self.scannable_uri1,
            response_save_loc=scan_request_response_loc,
            options={}
        )
        get_scan_info_save_loc = self.get_test_loc('scancodeio/get_scan_info.json')
        get_scan_data_save_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        ProcessScansCommand.process_scan(
            self.scannable_uri1,
            get_scan_info_save_loc=get_scan_info_save_loc,
            get_scan_data_save_loc=get_scan_data_save_loc
        )
        scan_exists_for_uri_save_loc = self.get_test_loc('scancodeio/scan_exists_for_uri.json')
        RequestScansCommand.process_scan(
            self.scannable_uri1,
            response_save_loc=scan_exists_for_uri_save_loc,
            options={}
        )
        scan_request_lookup_loc = self.get_test_loc('scancodeio/scan_request_lookup.json')
        response = scanning.query_scans(uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar', response_save_loc=scan_request_lookup_loc)
