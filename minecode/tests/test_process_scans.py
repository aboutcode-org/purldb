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

from minecode.management.commands.process_scans import Command
from minecode.management.commands.process_scans import get_scan_status
from minecode.management.commands.process_scans import index_package_files
from minecode.management.commands.process_scans import update_package_checksums
from minecode.management.commands.process_scans import _update_package_checksums
from minecode.management.scanning import Scan
from minecode.models import ScannableURI
from minecode.utils_test import MiningTestCase
from packagedb.models import Package
from packagedb.models import Resource


class ProcessScansTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            namespace='',
            name='wagon-api',
            version='20040705.181715'
        )

    def test_ProcessScansTest_get_scan_status(self):
        scan = Scan()
        scan.status = 'not_started'
        self.assertEqual(ScannableURI.SCAN_SUBMITTED, get_scan_status(scan))
        scan.status = 'queued'
        self.assertEqual(ScannableURI.SCAN_SUBMITTED, get_scan_status(scan))
        scan.status = 'running'
        self.assertEqual(ScannableURI.SCAN_IN_PROGRESS, get_scan_status(scan))
        scan.status = 'success'
        self.assertEqual(ScannableURI.SCAN_COMPLETED, get_scan_status(scan))
        scan.status = 'failure'
        self.assertEqual(ScannableURI.SCAN_FAILED, get_scan_status(scan))
        scan.status = 'stopped'
        self.assertEqual(ScannableURI.SCAN_FAILED, get_scan_status(scan))
        scan.status = 'stale'
        self.assertEqual(ScannableURI.SCAN_FAILED, get_scan_status(scan))
        scan.status = 'asdf'
        self.assertRaises(Exception, get_scan_status, scan)

    def test_ProcessScansTest_index_package_files(self):
        scan_data_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.loads(f.read())
        self.assertEqual(0, len(index_package_files(self.package1, scan_data)))
        result = Resource.objects.filter(package=self.package1)
        self.assertEqual(78, len(result))

    @patch('requests.get')
    def test_ProcessScansTest_process_scan(self, mock_get):
        # Set up mock responses
        mock_scan_info_response = Mock()
        scan_info_loc = self.get_test_loc('scancodeio/get_scan_info.json')
        with open(scan_info_loc, 'rb') as f:
            mock_scan_info_response.json.return_value = json.loads(f.read())

        mock_scan_data_response = Mock()
        scan_data_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        with open(scan_data_loc, 'rb') as f:
            mock_scan_data_response.json.return_value = json.loads(f.read())

        mock_scan_summary_response = Mock()
        scan_summary_loc = self.get_test_loc('scancodeio/scan_summary_response.json')
        with open(scan_summary_loc, 'rb') as f:
            mock_scan_summary_response.json.return_value = json.loads(f.read())

        mock_get.side_effect = [mock_scan_info_response, mock_scan_data_response, mock_scan_summary_response]

        # Set up ScannableURI
        scan_uuid = '54dc4afe-70ea-4f1c-9ed3-989efd9a991f'
        scannable_uri = ScannableURI.objects.create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_uuid=scan_uuid,
            scan_status=ScannableURI.SCAN_COMPLETED,
            package=self.package1
        )

        # Run test
        Command.process_scan(scannable_uri)

        # Make sure that we get license_expression and copyright from the summary
        self.assertEqual('apache-2.0', self.package1.license_expression)
        self.assertEqual('Copyright (c) Apache Software Foundation', self.package1.copyright)

        result = Resource.objects.filter(package=self.package1)
        self.assertEqual(78, len(result))
