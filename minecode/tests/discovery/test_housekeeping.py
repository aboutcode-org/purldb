#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import codecs
import json
import os
from io import StringIO

from mock import patch

from django.core import management
from django.test import TestCase as DjangoTestCase

import packagedb

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting

from discovery.management.commands.check_licenses import find_ambiguous_packages
from discovery.management.commands.run_map import map_uri
from discovery.management.commands.run_visit import visit_uri

from discovery.models import ResourceURI


class PackageLicenseCheckTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def check_expected_package_results(self, results, expected_loc, regen=False):
        """
        Check that `results` is equal to the expected data JSON data stored at
        location `expected_loc`.
        """
        if regen:
            with codecs.open(expected_loc, mode='wb', encoding='utf-8') as expect:
                json.dump(results, expect, indent=2, separators=(',', ': '))

        with codecs.open(expected_loc, mode='rb', encoding='utf-8') as expect:
            expected = json.load(expect)

        assert results == expected

    def test_find_ambiguous_packages_declared_license(self):
        packagedb.models.Package.objects.create(
            download_url='http://example.com',
            name='Foo',
            declared_license='apache and unknown',
            type='maven'
        )
        packages = [p.to_dict() for p in find_ambiguous_packages()]
        expected_loc = self.get_test_loc('housekeeping/declared_license_search_expected.json')
        self.check_expected_package_results(packages, expected_loc, regen=False)

    def test_find_ambiguous_packages_license_expression(self):
        packagedb.models.Package.objects.create(
            download_url='http://example.com',
            name='Foo',
            license_expression='apache and unknown',
            type='maven'
        )
        packages = [p.to_dict() for p in find_ambiguous_packages()]

        expected_loc = self.get_test_loc('housekeeping/license_expression_search_expected.json')
        self.check_expected_package_results(packages, expected_loc, regen=False)

    def test_find_ambiguous_packages_license_expression_ignore_uppercase(self):
        packagedb.models.Package.objects.create(
            download_url='http://example.com',
            name='Foo',
            license_expression='Unknown',
            type='maven'
        )
        packages = [p.to_dict() for p in find_ambiguous_packages()]

        expected_loc = self.get_test_loc('housekeeping/ignore_upper_case_search_expected.json')

        self.check_expected_package_results(packages, expected_loc, regen=False)

    def test_run_check_licenses_command(self):
        packagedb.models.Package.objects.create(
            download_url='http://example.com',
            name='Foo',
            license_expression='apache and unknown',
            type='maven'
        )
        results_loc = self.get_temp_file()
        expected_loc = self.get_test_loc('housekeeping/example_expected.json')

        output = StringIO()
        management.call_command('check_licenses', '-o', results_loc, stdout=output)
        self.assertTrue('Visited 1 packages\nFound 1 possible packages\nFound packages dumped to:' in output.getvalue())

        with open(results_loc) as results:
            res = json.load(results)
        self.check_expected_package_results(res, expected_loc, regen=False)

    def test_run_check_licenses_command_with_empty_package(self):
        output = StringIO()
        results_loc = self.get_temp_file()
        management.call_command('check_licenses', '-o', results_loc, stdout=output)
        self.assertTrue('Visited 0 packages\nFound 0 possible packages' in output.getvalue())

    def test_visit_and_map_using_pom(self):
        uri = 'http://repo1.maven.org/maven2/org/bytesoft/bytejta-supports/0.5.0-ALPHA4/bytejta-supports-0.5.0-ALPHA4.pom'
        test_loc = self.get_test_loc('housekeeping/bytejta-supports-0.5.0-ALPHA4.pom')

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)
            map_uri(resource_uri)
        packages = [p.to_dict() for p in find_ambiguous_packages()]
        expected_loc = self.get_test_loc('housekeeping/bytejta-supports-0.5.0-ALPHA4.pom_search_expected.json')
        self.check_expected_package_results(packages, expected_loc, regen=False)
