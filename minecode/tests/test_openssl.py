#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import datetime
import os

from mock import Mock
from mock import patch

from django.test import TestCase as DjangoTestCase

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.mappers.openssl import build_packages
from minecode.models import ResourceURI
from minecode.visitors import openssl


class OpenSSLVisitorsTest(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_OpenSSLVisitor(self):
        uri = 'https://ftp.openssl.org/'
        test_loc = self.get_test_loc('openssl/Index.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = openssl.OpenSSLVisitor(uri)
        expected_loc = self.get_test_loc(
            'openssl/expected_uri_openssl_index.json')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_OpenSSLVisitor_sub_folder(self):
        uri = 'https://ftp.openssl.org/source/'
        test_loc = self.get_test_loc('openssl/Indexof_source.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = openssl.OpenSSLVisitor(uri)
        expected_loc = self.get_test_loc(
            'openssl/expected_uri_openssl_sourceindex.json')
        self.check_expected_uris(uris, expected_loc, regen=False)


class OpenSSLTest(JsonBasedTesting, DjangoTestCase):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_OpenSSL_mapper(self):
        uri = 'https://ftp.openssl.org/snapshot/openssl-1.0.2-stable-SNAP-20180518.tar.gz'
        last_modified_date = '2014-11-19 17:49'
        last_modified_date = datetime.strptime(
            last_modified_date, '%Y-%m-%d %H:%M')
        resource_uri = ResourceURI.objects.insert(
            uri=uri, size='527', last_modified_date=last_modified_date)
        packages = build_packages(resource_uri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'openssl/openssl_mapper_expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)
