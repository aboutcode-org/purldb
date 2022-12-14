#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os

from django.test import TestCase as DjangoTestCase

from packagedcode import models as scan_models

from discovery.utils_test import JsonBasedTesting
from discovery.utils import is_int
from discovery.utils import stringify_null_purl_fields


class UtilsTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_stringify_null_purl_fields_with_missing_purl_fields(self):
        common_data = {
            'type': None
        }

        stringify_null_purl_fields(common_data)

        self.assertEqual(1, len(common_data))
        self.assertEqual('', common_data['type'])

    def test_stringify_null_purl_fields(self):
        common_data = {
            'type': None,
            'namespace': None,
            'name': None,
            'version': None,
            'qualifiers': None,
            'subpath': None
        }

        stringify_null_purl_fields(common_data)

        for d in common_data:
            self.assertIsNotNone(common_data[d])
            self.assertEqual('', common_data[d])

    def test_set_purl(self):
        common_data = dict(
            type='generic',
            name='openssl',
            description='The OpenSSL Project is a collaborative effort.',
        )
        package = scan_models.Package(**common_data)
        package.set_purl('pkg:generic/openssl@1.0.2o')
        self.assertEqual(None, package.namespace)
        self.assertEqual('generic', package.type)
        self.assertEqual('openssl', package.name)
        self.assertEqual('1.0.2o', package.version)
        self.assertEqual({}, package.qualifiers)
        self.assertEqual(None, package.subpath)

    def test_is_int(self):
        self.assertTrue(is_int(0))
        self.assertFalse(is_int('a'))
