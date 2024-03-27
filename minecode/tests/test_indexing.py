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

from matchcode.models import ExactFileIndex

from minecode.management import indexing
from minecode.models import ScannableURI
from minecode.utils_test import MiningTestCase
from minecode.utils_test import JsonBasedTesting
from minecode.tests import FIXTURES_REGEN
from packagedb.models import Package
from packagedb.models import Resource


class IndexingTest(MiningTestCase, JsonBasedTesting):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            type='maven',
            namespace='',
            name='wagon-api',
            version='20040705.181715'
        )

    def test_indexing_index_package_files(self):
        scan_data_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.loads(f.read())
        self.assertEqual(0, len(indexing.index_package_files(self.package1, scan_data)))
        result = Resource.objects.filter(package=self.package1)
        self.assertEqual(64, len(result))
        results = [r.to_dict() for r in result]
        expected_resources_loc = self.get_test_loc('scancodeio/get_scan_data_expected_resources.json')
        self.check_expected_results(results, expected_resources_loc, regen=FIXTURES_REGEN)

    def test_indexing_index_package(self):
        scan_data_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.load(f)

        scan_summary_loc = self.get_test_loc('scancodeio/scan_summary_response.json')
        with open(scan_summary_loc, 'rb') as f:
            scan_summary = json.load(f)

        project_extra_data = {
            'md5': 'md5',
            'sha1': 'sha1',
            'sha256': 'sha256',
            'sha512': 'sha512',
            'size': 100,
        }

        # Set up ScannableURI
        scannable_uri = ScannableURI.objects.create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_status=ScannableURI.SCAN_COMPLETED,
            package=self.package1
        )

        self.assertFalse(self.package1.md5)
        self.assertFalse(self.package1.sha1)
        self.assertFalse(self.package1.sha256)
        self.assertFalse(self.package1.sha512)
        self.assertFalse(self.package1.size)
        self.assertFalse(self.package1.declared_license_expression)
        self.assertFalse(self.package1.copyright)
        self.assertEqual(0, Resource.objects.all().count())

        # Run test
        indexing.index_package(
            scannable_uri,
            self.package1,
            scan_data,
            scan_summary,
            project_extra_data,
        )

        # Make sure that Package data is updated
        self.assertEqual('apache-2.0', self.package1.declared_license_expression)
        self.assertEqual('Copyright (c) Apache Software Foundation', self.package1.copyright)
        self.assertEqual('md5', self.package1.md5)
        self.assertEqual('sha1', self.package1.sha1)
        self.assertEqual('sha256', self.package1.sha256)
        self.assertEqual('sha512', self.package1.sha512)
        self.assertEqual(100, self.package1.size)

        result = Resource.objects.filter(package=self.package1)
        self.assertEqual(64, result.count())
        result = ExactFileIndex.objects.filter(package=self.package1)
        self.assertEqual(45, result.count())
