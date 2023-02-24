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

    def test_ProcessScansTest_get_scan_status(self):
        scan = Scan()
        scan.status = 'not started yet'
        self.assertEqual(ScannableURI.SCAN_SUBMITTED, get_scan_status(scan))
        scan.status = 'in progress'
        self.assertEqual(ScannableURI.SCAN_IN_PROGRESS, get_scan_status(scan))
        scan.status = 'completed'
        self.assertEqual(ScannableURI.SCAN_COMPLETED, get_scan_status(scan))
        scan.status = 'failed'
        self.assertEqual(ScannableURI.SCAN_FAILED, get_scan_status(scan))
        scan.status = 'asdf'
        self.assertRaises(Exception, get_scan_status, scan)

    def test_ProcessScansTest_update_package_checksums_update_all(self):
        test_sha1 = 'beef'
        test_md5 = 'feed'
        test_size = 3
        package = Package.objects.create(download_url='example.com', name='Foo', version='1.23')
        scan = Scan(sha1=test_sha1, md5=test_md5, size=test_size)
        scan_errors = update_package_checksums(package, scan)
        self.assertFalse(scan_errors)
        result = Package.objects.get(download_url='example.com')
        self.assertEqual(test_sha1, result.sha1)
        self.assertEqual(test_md5, result.md5)
        self.assertEqual(test_size, result.size)

    def test_ProcessScansTest_update_package_checksums_mismatched_checksums(self):
        expected_sha1 = 'fe12'
        test_sha1 = 'beef'
        test_md5 = 'feed'
        test_size = 3
        package = Package.objects.create(
            download_url='example.com',
            name='Foo',
            version='1.23',
            sha1=expected_sha1,
        )
        scan = Scan(sha1=test_sha1, md5=test_md5, size=test_size)
        scan_errors = update_package_checksums(package, scan)
        self.assertTrue(scan_errors)
        result = Package.objects.get(download_url='example.com')
        self.assertEqual(expected_sha1, result.sha1)
        self.assertFalse(result.md5)
        self.assertFalse(result.size)

    def test_ProcessScansTest__update_package_checksums_mismatched_sha1(self):
        expected_sha1 = 'fe12'
        test_sha1 = 'beef'
        test_md5 = 'feed'
        test_size = 3
        package = Package.objects.create(
            download_url='example.com',
            name='Foo',
            version='1.23',
            sha1=expected_sha1
        )
        scan = Scan(sha1=test_sha1, md5=test_md5, size=test_size)
        self.assertRaises(Exception, _update_package_checksums, package, scan)

    def test_ProcessScansTest__update_package_checksums_update(self):
        test_sha1 = 'beef'
        test_md5 = 'feed'
        test_size = 3
        package = Package.objects.create(download_url='example.com', name='Foo', version='1.23')
        scan = Scan(sha1=test_sha1, md5=test_md5, size=test_size)
        updated = _update_package_checksums(package, scan)
        self.assertTrue(updated)
        results = Package.objects.filter(sha1=test_sha1)
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertTrue(test_sha1, result.sha1)
        self.assertTrue(test_md5, result.md5)
        self.assertTrue(test_size, result.size)

    def test_ProcessScansTest__update_package_checksums_no_update(self):
        test_sha1 = 'beef'
        test_md5 = 'feed'
        test_size = 3
        package = Package.objects.create(
            download_url='example.com',
            name='Foo',
            version='1.23',
            sha1=test_sha1,
            md5=test_md5,
            size=test_size
        )
        scan = Scan(sha1=test_sha1, md5=test_md5, size=test_size)
        result = _update_package_checksums(package, scan)
        self.assertFalse(result)

    def test_ProcessScansTest_index_package_files(self):
        scan_data_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.loads(f.read())
        package = Package.objects.create(download_url='example.com', name='Foo', version='1.23')
        self.assertEqual(0, len(index_package_files(package, scan_data)))
        result = Resource.objects.filter(package=package)
        self.assertEqual(65, len(result))

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

        mock_get.side_effect = [mock_scan_info_response, mock_scan_data_response]

        # Set up Package and ScannableURI
        scan_uuid = '177eb27a-25d2-4ef0-b608-5a84ea9b1ef1'
        package = Package.objects.create(download_url='example.com', name='Foo', version='1.23')
        scannable_uri = ScannableURI.objects.create(
            uri='http://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_uuid=scan_uuid,
            scan_status=ScannableURI.SCAN_COMPLETED,
            package=package
        )

        # Run test
        Command.process_scan(scannable_uri)

        self.assertEqual('feff0d7bacd11d37a9c96daed87dc1db163065b1', package.sha1)
        self.assertEqual('57431f2f6d5841eebdb964b04091b8ed', package.md5)
        self.assertEqual(47069, package.size)

        result = Resource.objects.filter(package=package)
        self.assertEqual(65, len(result))
