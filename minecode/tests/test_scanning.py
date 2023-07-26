# -*- coding: utf-8 -*-
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

import attr
import mock

from django.test import TestCase as DjangoTestCase

from minecode.management import scanning
from minecode.utils_test import JsonBasedTesting
from packagedb.models import Package


class ScanCodeIOAPIHelperFunctionTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            type='maven',
            namespace='maven',
            name='wagon-api',
            version='20040705.181715',
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
        )

    @mock.patch('requests.get')
    def testscanning_query_scans(self, mock_get):
        mock_get.return_value = mock.Mock(ok=True)
        scan_info_response_loc = self.get_test_loc('scancodeio/scan_request_lookup.json')
        with open(scan_info_response_loc, 'rb') as f:
            mock_get.return_value.json.return_value = json.loads(f.read())

        api_url = 'http://127.0.0.1:8001/api/'
        api_auth_headers = {}
        uri = 'https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar'
        response = scanning.query_scans(uri=uri, api_url=api_url, api_auth_headers=api_auth_headers)
        result = scanning.Scan.from_response(**response)

        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/c3b8d1ab-4811-4ced-84af-080997ef1a1a/',
            uuid='c3b8d1ab-4811-4ced-84af-080997ef1a1a',
            run_uuid='336e18e3-fd68-4375-9bf2-87090dc5c726',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-05-19T00:45:29.451929Z',
            task_start_date='2023-05-19T00:45:29.461599Z',
            task_end_date='2023-05-19T00:45:39.251824Z',
            task_exitcode=0,
            status='success',
            execution_time=9
        )
        result = attr.asdict(result)
        expected = attr.asdict(expected)
        self.assertEqual(expected, result)

    @mock.patch('requests.post')
    def testscanning_submit_scan(self, mock_post):
        test_loc = self.get_test_loc('scancodeio/scan_request_response.json')
        mock_post.return_value = mock.Mock(ok=True)
        with open(test_loc, 'rb') as f:
            mock_post.return_value.json.return_value = json.loads(f.read())
        api_url = 'http://127.0.0.1:8001/api/'
        api_auth_headers = {}
        uri = 'https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar'
        result = scanning.submit_scan(
            uri=uri,
            package=self.package1,
            api_url=api_url,
            api_auth_headers=api_auth_headers
        )
        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/c3b8d1ab-4811-4ced-84af-080997ef1a1a/',
            uuid='c3b8d1ab-4811-4ced-84af-080997ef1a1a',
            run_uuid='336e18e3-fd68-4375-9bf2-87090dc5c726',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-05-19T00:45:29.451929Z',
            task_start_date=None,
            task_end_date=None,
            task_exitcode=None,
            status='not_started',
            execution_time=None,
        )
        expected = attr.asdict(expected)
        result = attr.asdict(result)
        self.assertEqual(expected, result)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def testscanning_submit_scan_uri_exists(self, mock_post, mock_get):
        self.maxDiff = None
        mock_post.return_value = mock.Mock(ok=False)
        scan_request_response_loc = self.get_test_loc('scancodeio/scan_exists_for_uri.json')
        with open(scan_request_response_loc, 'rb') as f:
            mock_post.return_value.json.return_value = json.loads(f.read())

        mock_get.return_value = mock.Mock(ok=True)
        scan_info_response_loc = self.get_test_loc('scancodeio/scan_request_response.json')
        with open(scan_info_response_loc, 'rb') as f:
            mock_get.return_value.json.return_value = json.loads(f.read())

        api_url = 'http://127.0.0.1:8001/api/'
        api_auth_headers = {}
        uri = 'https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar'
        result = scanning.submit_scan(
            uri=uri,
            package=self.package1,
            api_url=api_url,
            api_auth_headers=api_auth_headers
        )

        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/c3b8d1ab-4811-4ced-84af-080997ef1a1a/',
            uuid='c3b8d1ab-4811-4ced-84af-080997ef1a1a',
            run_uuid='336e18e3-fd68-4375-9bf2-87090dc5c726',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-05-19T00:45:29.451929Z',
            task_start_date=None,
            task_end_date=None,
            task_exitcode=None,
            status='not_started',
            execution_time=None,
        )

        expected = attr.asdict(expected)
        result = attr.asdict(result)
        self.assertEqual(expected, result)

    def testscanning_get_scan_url(self):
        scan_uuid = '177eb27a-25d2-4ef0-b608-5a84ea9b1ef1'
        api_url_projects = 'http://127.0.0.1:8001/api/projects/'
        suffix = 'results'
        result = scanning.get_scan_url(scan_uuid=scan_uuid, api_url=api_url_projects)
        expected = 'http://127.0.0.1:8001/api/projects/177eb27a-25d2-4ef0-b608-5a84ea9b1ef1/'
        self.assertEqual(expected, result)
        result_with_suffix = scanning.get_scan_url(scan_uuid=scan_uuid, api_url=api_url_projects, suffix=suffix)
        expected_with_suffix = 'http://127.0.0.1:8001/api/projects/177eb27a-25d2-4ef0-b608-5a84ea9b1ef1/results/'
        self.assertEqual(expected_with_suffix, result_with_suffix)

    @mock.patch('requests.get')
    def testscanning_get_scan_info(self, mock_get):
        test_loc = self.get_test_loc('scancodeio/get_scan_info.json')
        mock_get.return_value = mock.Mock(ok=True)
        with open(test_loc, 'rb') as f:
            mock_get.return_value.json.return_value = json.loads(f.read())
        scan_uuid = '54dc4afe-70ea-4f1c-9ed3-989efd9a991f'
        api_url = 'http://127.0.0.1:8001/api/'
        api_auth_headers = {}
        result = scanning.get_scan_info(scan_uuid=scan_uuid, api_url=api_url, api_auth_headers=api_auth_headers)
        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/c3b8d1ab-4811-4ced-84af-080997ef1a1a/',
            uuid='c3b8d1ab-4811-4ced-84af-080997ef1a1a',
            run_uuid='336e18e3-fd68-4375-9bf2-87090dc5c726',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-05-19T00:45:29.451929Z',
            task_start_date='2023-05-19T00:45:29.461599Z',
            task_end_date='2023-05-19T00:45:39.251824Z',
            task_exitcode=0,
            status='success',
            execution_time=9,
            md5='57431f2f6d5841eebdb964b04091b8ed',
            sha1='feff0d7bacd11d37a9c96daed87dc1db163065b1',
            sha256='05155c2c588ac5922d930eeb1e8a1da896956f4696ae758d110708e9f095baba',
            sha512='4431f237bcdfee5d2b86b1b3f01c8abaa160d5b7007c63e6281845a3f920d89fdb2e4044f97694ddef91e174d9dd30e5016bbad46eec2d68af200a47e9cedd85',
            sha1_git='ad18d88bdae8449e7c170f8e7db1bfe336dbb4e0',
            filename='wagon-api-20040705.181715.jar',
            size=47069,
        )
        expected = attr.asdict(expected)
        result = attr.asdict(result)
        self.assertEqual(expected, result)

    @mock.patch('requests.get')
    def testscanning_get_scan_data(self, mock_get):
        test_loc = self.get_test_loc('scancodeio/get_scan_data.json')
        mock_get.return_value = mock.Mock(ok=True)
        with open(test_loc, 'rb') as f:
            mock_get.return_value.json.return_value = json.loads(f.read())
        scan_uuid = '54dc4afe-70ea-4f1c-9ed3-989efd9a991f'
        api_url = 'http://127.0.0.1:8001/api/'
        api_auth_headers = {}
        expected_loc = self.get_test_loc('scancodeio/get_scan_data_expected.json')
        result = scanning.get_scan_data(scan_uuid=scan_uuid, api_url=api_url, api_auth_headers=api_auth_headers)
        with open(expected_loc, 'rb') as f:
            expected = json.loads(f.read())
        self.assertEqual(expected['files'], result['files'])
