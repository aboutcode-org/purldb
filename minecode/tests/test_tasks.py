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

from django.test import TestCase
from unittest import mock

from minecode.models import ScannableURI
from packagedb.models import Package
from minecode.utils_test import JsonBasedTesting
from minecode import tasks


class MinecodeTasksTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://test-url.com/package1.tar.gz',
            type='type1',
            name='name1',
            version='1.0',
        )
        self.scannable_uri1 = ScannableURI.objects.create(
            uri='https://test-url.com/package1.tar.gz',
            package=self.package1
        )
        self.project_extra_data1 = {
            'md5': 'md5',
            'sha1': 'sha1',
            'sha256': 'sha256',
            'sha512': 'sha512',
            'size': 100,
        }

    @mock.patch('os.remove')
    def test_minecode_tasks_process_scan_results(self, mock_delete):
        mock_delete.side_effect = [None, None]

        self.assertFalse(self.package1.md5)
        self.assertFalse(self.package1.sha1)
        self.assertFalse(self.package1.sha256)
        self.assertFalse(self.package1.sha512)
        self.assertFalse(self.package1.size)
        self.assertFalse(self.package1.declared_license_expression)
        self.assertFalse(self.package1.copyright)
        self.assertEquals(0, self.package1.resources.count())
        scan_file_location = self.get_test_loc('scancodeio/get_scan_data.json')
        summary_file_location = self.get_test_loc('scancodeio/scan_summary_response.json')
        project_extra_data = json.dumps(self.project_extra_data1)
        tasks.process_scan_results(
            self.scannable_uri1.uuid,
            scan_results_location=scan_file_location,
            scan_summary_location=summary_file_location,
            project_extra_data=project_extra_data,
        )
        self.package1.refresh_from_db()
        self.assertEqual('md5', self.package1.md5)
        self.assertEqual('sha1', self.package1.sha1)
        self.assertEqual('sha256', self.package1.sha256)
        self.assertEqual('sha512', self.package1.sha512)
        self.assertEqual(100, self.package1.size)
        self.assertEqual('apache-2.0', self.package1.declared_license_expression)
        self.assertEqual('Copyright (c) Apache Software Foundation', self.package1.copyright)
        self.assertFalse(self.scannable_uri1.scan_error)
        self.assertEqual(64, self.package1.resources.count())
