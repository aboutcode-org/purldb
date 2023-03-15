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

from django.db.models import Q

from minecode.management.commands.request_scans import Command
from minecode.utils_test import MiningTestCase
from packagedb.models import Package
from minecode.models import ScannableURI


class RequestScansTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            namespace='',
            name='wagon-api',
            version='20040705.181715'
        )

    @patch('requests.post')
    def test_RequestScansTest_request_scan(self, mock_post):
        # Set up mock responses
        mock_scan_request_response = Mock()
        scan_request_loc = self.get_test_loc('scancodeio/scan_request_response.json')
        with open(scan_request_loc, 'rb') as f:
            mock_scan_request_response.json.return_value = json.loads(f.read())

        mock_post.side_effect = [mock_scan_request_response]

        # Set up ScannableURI
        scannable_uri1 = ScannableURI.objects.create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_status=ScannableURI.SCAN_NEW,
            package=self.package1
        )

        for scannable_uri in ScannableURI.objects.all():
            # Run test
            Command.process_scan(scannable_uri, options={})

        result = ScannableURI.objects.get(uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar')
        self.assertEqual(ScannableURI.SCAN_SUBMITTED, result.scan_status)

    def test_RequestScansTest_limit_scan_request(self):
        # Set up Package and ScannableURI
        package1 = Package.objects.create(download_url='example.com', name='Foo', version='1.23')
        scannable_uri1 = ScannableURI.objects.create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_status=ScannableURI.SCAN_NEW,
            package=package1
        )

        for scannable_uri in ScannableURI.objects.all():
            # Run test, no API call should be made because `max_scan_requests` is 0
            Command.process_scan(scannable_uri, options={'max_scan_requests': 0})

        result = ScannableURI.objects.get(uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar')
        self.assertEqual(ScannableURI.SCAN_NEW, result.scan_status)
