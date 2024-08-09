#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import json
import os
import re

from django.test import TestCase as DjangoTestCase
from mock import Mock
from mock import patch

from minecode import mappers
from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting
from minecode.visitors import apache
from minecode.tests import FIXTURES_REGEN


class ApacheVistorTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_ApacheDistIndexVisitor(self):
        uri = 'http://apache.org/dist/zzz/find-ls.gz'
        test_loc = self.get_test_loc('apache/find-ls.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = apache.ApacheDistIndexVisitor(uri)

        expected_loc = self.get_test_loc('apache/find-ls.gz_uris-expected.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_ApacheChecksumVisitor(self):
        uri = 'http://archive.apache.org/dist/abdera/1.1.3/apache-abdera-1.1.3-src.zip.md5'
        test_loc = self.get_test_loc('apache/apache-abdera-1.1.3-src.zip.md5')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = apache.ApacheChecksumVisitor(uri)

        self.assertEqual(None, uris)
        self.assertEqual(b'0b5f2c334916c289f06c03f8577a9879', data)

    def test_ApacheChecksumVisitor_2(self):
        uri = 'http://archive.apache.org/dist/groovy/2.4.6/distribution/apache-groovy-docs-2.4.6.zip.md5'
        test_loc = self.get_test_loc('apache/apache-groovy-docs-2.4.6.zip.md5')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = apache.ApacheChecksumVisitor(uri)

        self.assertEqual(None, uris)
        self.assertEqual(b'c7a2d3becea1d28b518528f8204b8d2a', data)

    def test_ApacheProjectsJsonVisitor(self):
        uri = 'https://projects.apache.org/json/foundation/projects.json'
        test_loc = self.get_test_loc('apache/projects.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            uris, result, _ = apache.ApacheProjectsJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/projects_uris-expected.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

        self.check_expected_results(result, test_loc, regen=FIXTURES_REGEN)

    def test_ApacheSingleProjectJsonVisitor(self):
        uri = 'https://projects.apache.org/json/projects/ant-dotnet.json'
        test_loc = self.get_test_loc('apache/ant-dotnet.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            _, result, _ = apache.ApacheSingleProjectJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/ant-dotnet_expected.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_ApacheSingleProjectJsonVisitor_error1_json(self):
        uri = 'https://projects.apache.org/json/projects/felix.json'
        test_loc = self.get_test_loc('apache/felix.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            _, result, _ = apache.ApacheSingleProjectJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/felix_expected.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_ApacheSingleProjectJsonVisitor_error2_json(self):
        uri = 'https://projects.apache.org/json/projects/attic-mrunit.json'
        test_loc = self.get_test_loc('apache/attic-mrunit.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            _, result, _ = apache.ApacheSingleProjectJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/attic-mrunit_expected.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_ApacheSingleProjectJsonVisitor_error3_json(self):
        uri = 'https://projects.apache.org/json/projects/metamodel.json'
        test_loc = self.get_test_loc('apache/metamodel.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            _, result, _ = apache.ApacheSingleProjectJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/metamodel_expected.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_ApachePodlingsJsonVisitor(self):
        uri = 'https://projects.apache.org/json/foundation/podlings.json'
        test_loc = self.get_test_loc('apache/podlings.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # note: remove the "()" below once this visitor route is made active again
            uris, result, _ = apache.ApachePodlingsJsonVisitor()(uri)

        expected_loc = self.get_test_loc('apache/podlings_expected_uris.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

        expected_loc = self.get_test_loc('apache/podlings_expected.json')
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)


class ApacheMapperTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_package_from_download(self):
        package = mappers.apache.build_package_from_download(
            'http://archive.apache.org/dist/groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip',
            'pkg:apache/groovy@2.4.6')
        expected_loc = self.get_test_loc('apache/map-groovy_expected.json')
        self.check_expected_results(package.to_dict(), expected_loc, regen=FIXTURES_REGEN)

    def test_build_package_from_download2(self):
        package = mappers.apache.build_package_from_download(
            'http://archive.apache.org/dist/turbine/maven/turbine-webapp-2.3.3-1.0.0-source-release.zip',
            'pkg:apache/turbine-webapp@2.3.3-1.0.0-source-release')
        expected_loc = self.get_test_loc('apache/map-turbine-webapp_expected.json')
        self.check_expected_results(package.to_dict(), expected_loc, regen=FIXTURES_REGEN)

    # TODO: add tests for checksums

    def test_build_packages_from_projects_json(self):
        with open(self.get_test_loc('apache/projects.json')) as projectsjson_meta:
            metadata = json.load(projectsjson_meta, object_pairs_hook=OrderedDict)
        packages = mappers.apache.build_packages_from_projects(metadata)
        packages = [p.to_dict() for p in packages]

        expected_loc = self.get_test_loc('apache/projects_expected.json')
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_from_one_podling_json(self):
        with open(self.get_test_loc('apache/podling_amaterasu.json')) as podlings_meta:
            metadata = json.load(podlings_meta, object_pairs_hook=OrderedDict)
        packages = mappers.apache.build_packages_from_podlings(metadata, purl='pkg:apache-podlings/amaterasu')
        packages = [p.to_dict() for p in packages]

        expected_loc = self.get_test_loc('apache/podling_amaterasu_expected.json')
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    # TODO: add real mapper class tests c

    def test_regex_1(self):
        regex = re.compile(r'^https?://(archive\.)?apache\.org/dist/.*$')
        result = re.match(regex, 'http://archive.apache.org/dist/groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip')
        self.assertTrue(result)

    def test_regex_2(self):
        regex = re.compile(r'^https?://(archive\.)?apache\.org/dist/.*$')
        result = re.match(regex, 'https://apache.org/dist/chemistry/opencmis/1.1.0/chemistry-opencmis-dist-1.1.0-server-webapps.zip')
        self.assertTrue(result)
