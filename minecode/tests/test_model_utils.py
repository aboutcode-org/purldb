#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import timedelta
import os

from django.utils import timezone

from minecode.model_utils import merge_or_create_package
from minecode.utils_test import JsonBasedTesting, MiningTestCase
from packagedb.models import Package
from packagedcode.maven import _parse


class ModelUtilsTestCase(MiningTestCase, JsonBasedTesting):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        pom_loc = self.get_test_loc('maven/pom/pulsar-2.5.1.pom')
        self.scanned_package = _parse('maven_pom', 'maven', 'Java', location=pom_loc)
        self.scanned_package.download_url = 'https://repo1.maven.org/maven2/org/apache/pulsar/pulsar/2.5.1/pulsar-2.5.1.jar'

    def test_merge_or_create_package_create_package(self):
        self.assertEqual(0, Package.objects.all().count())
        package, created, merged, map_error = merge_or_create_package(
            self.scanned_package,
            visit_level=50
        )
        self.assertEqual(1, Package.objects.all().count())
        self.assertEqual(package, Package.objects.all().first())
        self.assertTrue(created)
        self.assertFalse(merged)
        self.assertEqual('', map_error)
        self.assertTrue(package.created_date)
        self.assertTrue(package.last_modified_date)
        expected_loc = self.get_test_loc('model_utils/created_package.json')
        self.check_expected_results(
            package.to_dict(),
            expected_loc,
            fields_to_remove=['package_sets'],
            regen=False,
        )

    def test_merge_or_create_package_merge_package(self):
        # ensure fields get updated
        # ensure history is properly updated
        package = Package.objects.create(
            type='maven',
            namespace='org.apache.pulsar',
            name='pulsar',
            version='2.5.1',
            download_url='https://repo1.maven.org/maven2/org/apache/pulsar/pulsar/2.5.1/pulsar-2.5.1.jar',
        )
        before_merge_loc = self.get_test_loc('model_utils/before_merge.json')
        self.check_expected_results(
            package.to_dict(),
            before_merge_loc,
            fields_to_remove=['package_sets'],
            regen=False,
        )
        package, created, merged, map_error = merge_or_create_package(
            self.scanned_package,
            visit_level=50
        )
        self.assertEqual(1, Package.objects.all().count())
        self.assertEqual(package, Package.objects.all().first())
        self.assertFalse(created)
        self.assertTrue(merged)
        self.assertEqual('', map_error)
        expected_loc = self.get_test_loc('model_utils/after_merge.json')
        self.check_expected_results(
            package.to_dict(),
            expected_loc,
            fields_to_remove=['package_sets'],
            regen=False,
        )
        history = package.get_history()
        self.assertEqual(1, len(history))
        entry = history[0]
        timestamp = entry['timestamp']
        message = entry['message']
        self.assertEqual(
            'Existing Package values replaced due to ResourceURI mining level via map_uri().',
            message,
        )
        last_modified_date_formatted = package.last_modified_date.strftime("%Y-%m-%d-%H:%M:%S")
        self.assertEqual(timestamp, last_modified_date_formatted)
