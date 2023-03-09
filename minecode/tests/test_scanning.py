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

from minecode.management import scanning
from minecode.utils_test import JsonBasedTesting


class ScanCodeIOAPIHelperFunctionTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

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
            url='http://127.0.0.1:8001/api/projects/54dc4afe-70ea-4f1c-9ed3-989efd9a991f/',
            uuid='54dc4afe-70ea-4f1c-9ed3-989efd9a991f',
            run_uuid='4711ea01-d3b1-4ce4-972b-859ac9c1d391',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-03-08T23:35:45.679962Z',
            task_start_date='2023-03-08T23:35:45.687840Z',
            task_end_date='2023-03-08T23:35:56.780375Z',
            task_exitcode=0,
            status='success',
            execution_time=11
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
        result = scanning.submit_scan(uri=uri, api_url=api_url, api_auth_headers=api_auth_headers)
        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/54dc4afe-70ea-4f1c-9ed3-989efd9a991f/',
            uuid='54dc4afe-70ea-4f1c-9ed3-989efd9a991f',
            run_uuid='4711ea01-d3b1-4ce4-972b-859ac9c1d391',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-03-08T23:35:45.679962Z',
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
        result = scanning.submit_scan(uri=uri, api_url=api_url, api_auth_headers=api_auth_headers)

        expected = scanning.Scan(
            url='http://127.0.0.1:8001/api/projects/54dc4afe-70ea-4f1c-9ed3-989efd9a991f/',
            uuid='54dc4afe-70ea-4f1c-9ed3-989efd9a991f',
            run_uuid='4711ea01-d3b1-4ce4-972b-859ac9c1d391',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-03-08T23:35:45.679962Z',
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
            url='http://127.0.0.1:8001/api/projects/54dc4afe-70ea-4f1c-9ed3-989efd9a991f/',
            uuid='54dc4afe-70ea-4f1c-9ed3-989efd9a991f',
            run_uuid='4711ea01-d3b1-4ce4-972b-859ac9c1d391',
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            created_date='2023-03-08T23:35:45.679962Z',
            task_start_date='2023-03-08T23:35:45.687840Z',
            task_end_date='2023-03-08T23:35:56.780375Z',
            task_exitcode=0,
            status='success',
            execution_time=11,
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
