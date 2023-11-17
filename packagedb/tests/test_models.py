#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from dateutil.parser import parse as dateutil_parse

from django.db import IntegrityError
from django.test import TransactionTestCase
from django.utils import timezone

from packagedb.models import Package
from packagedb.models import Resource


class ResourceModelTestCase(TransactionTestCase):
    def setUp(self):
        self.package = Package.objects.create(download_url='test-pkg.com')
        self.resource_paths = [
            'root/',
            'root/test.json'
        ]

    def tearDown(self):
        Package.objects.all().delete()
        Resource.objects.all().delete()

    def test_resource_is_created_on_a_package(self):
        Resource.objects.create(package=self.package, path=self.resource_paths[0])

        self.assertEqual(1, Resource.objects.all().count())

    def test_resources_are_created_on_a_package(self):
        for path in self.resource_paths:
            Resource.objects.create(package=self.package, path=path)

        self.assertEqual(2, Resource.objects.all().count())

    def test_duplicate_resources_are_not_created(self):
        for path in self.resource_paths:
            Resource.objects.create(package=self.package, path=path)
        for path in self.resource_paths:
            self.assertRaises(IntegrityError, Resource.objects.create, package=self.package, path=path)

        self.assertEqual(2, Resource.objects.all().count())


class PackageModelHistoryFieldTestCase(TransactionTestCase):
    def setUp(self):
        self.test_package = Package.objects.create(
                download_url='https://test.com',
        )
        self.message0 = 'test-message0'
        self.message1 = 'test-message1'
        self.message2 = 'test-message2'

    def test_history_field_append_and_get_one_item(self):
        self.test_package.append_to_history(self.message0)

        expected_date = timezone.now().strftime('%Y-%m-%d')
        expected_message = self.message0

        history = self.test_package.get_history()[0]

        self.assertIn(expected_date, history.get('timestamp'))
        self.assertEqual(expected_message, history.get('message'))

    def test_history_field_append_and_get_multiple_items(self):
        self.test_package.append_to_history(self.message0)
        self.test_package.append_to_history(self.message1)
        self.test_package.append_to_history(self.message2)

        expected_date = timezone.now().strftime('%Y-%m-%d')
        expected_messages = [
            self.message0,
            self.message1,
            self.message2,
        ]

        for expected_message, entry in zip(expected_messages, self.test_package.get_history()):
            self.assertIn(expected_date, entry.get('timestamp'))
            self.assertEqual(expected_message, entry.get('message'))


class PackageModelTestCase(TransactionTestCase):
    def setUp(self):
        self.created_package_download_url = 'https://created-example.com'
        self.inserted_package_download_url = 'https://inserted-example.com'

        self.created_package_data = {
            'download_url': self.created_package_download_url,
            'type': 'generic',
            'namespace': 'generic',
            'name': 'Foo',
            'version': '12.34',
        }

        self.inserted_package_data = {
            'download_url': self.inserted_package_download_url,
            'type': 'generic',
            'namespace': 'generic',
            'name': 'Bar',
            'version': '12.34',
        }

        self.created_package = Package.objects.create(**self.created_package_data)
        self.inserted_package = Package.objects.insert(**self.inserted_package_data)

    def test_package_download_url_is_unique(self):
        self.assertIsNone(Package.objects.insert(download_url=self.created_package_download_url))
        self.assertIsNone(Package.objects.insert(download_url=self.inserted_package_download_url))

    def test_packagedb_package_model_history_field(self):
        self.created_package.append_to_history('test-message')

        for entry in self.created_package.get_history():
            self.assertEqual('test-message', entry.get('message'))

    def test_packagedb_package_model_get_all_versions(self):
        p1 = Package.objects.create(download_url='http://a.a', type='generic', name='name', version='1.0')
        p2 = Package.objects.create(download_url='http://b.b', type='generic', name='name', version='2.0')
        p3 = Package.objects.create(download_url='http://c.c', type='generic', name='name', version='3.0')
        p4 = Package.objects.create(download_url='http://d.d', type='generic', namespace='space', name='name',
                                    version='4.0')

        self.assertEqual([p1, p2, p3], list(p1.get_all_versions()))
        self.assertEqual([p1, p2, p3], list(p2.get_all_versions()))
        self.assertEqual([p1, p2, p3], list(p3.get_all_versions()))
        self.assertEqual([p4], list(p4.get_all_versions()))

    def test_packagedb_package_model_get_latest_version(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        p2 = Package.objects.create(download_url='http://b.b', name='name', version='2.0')
        p3 = Package.objects.create(download_url='http://c.c', name='name', version='3.0')
        p4 = Package.objects.create(download_url='http://d.d', namespace='space', name='name',
                                    version='4.0')

        self.assertEqual(p3, p1.get_latest_version())
        self.assertEqual(p3, p2.get_latest_version())
        self.assertEqual(p3, p3.get_latest_version())
        self.assertEqual(p4, p4.get_latest_version())

    def test_packagedb_package_model_update_field(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        self.assertFalse(p1.history)
        self.assertEquals('', p1.namespace)
        package, updated_field = p1.update_field(field='namespace', value='test')
        self.assertEqual(updated_field, 'namespace')
        self.assertEqual('test', p1.namespace)
        self.assertEqual(1, len(p1.history))
        expected_history_entry = {
            'message': 'Package field values have been updated.',
            'data': {
                'updated_fields':
                [
                    {
                        'field': 'namespace',
                        'old_value': '',
                        'new_value': 'test'
                    }
                ]
            }
        }
        history_entry = p1.history[0]
        history_entry.pop('timestamp')
        self.assertEqual(expected_history_entry, history_entry)

    def test_packagedb_package_model_update_field(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        self.assertFalse(p1.history)
        self.assertEquals('', p1.namespace)
        package, updated_field = p1.update_field(field='namespace', value='test')
        self.assertEqual(updated_field, ['namespace', 'history'])
        self.assertEqual('test', p1.namespace)
        self.assertEqual(1, len(p1.history))
        expected_history_entry = {
            'message': 'Package field values have been updated.',
            'data': {
                'updated_fields':
                [
                    {
                        'field': 'namespace',
                        'old_value': '',
                        'new_value': 'test'
                    }
                ]
            }
        }
        history_entry = p1.history[0]
        history_entry.pop('timestamp')
        self.assertEqual(expected_history_entry, history_entry)

    def test_packagedb_package_model_update_fields(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        self.assertFalse(p1.history)
        self.assertEquals('', p1.namespace)
        self.assertEquals(None, p1.homepage_url)
        package, updated_fields = p1.update_fields(namespace='test', homepage_url='https://example.com')
        self.assertEqual(
            sorted(updated_fields),
            sorted(['homepage_url', 'history', 'namespace'])
        )
        self.assertEqual('test', p1.namespace)
        self.assertEqual('https://example.com', p1.homepage_url)
        self.assertEqual(1, len(p1.history))
        expected_history_entry = {
            'message': 'Package field values have been updated.',
            'data': {
                'updated_fields':
                [
                    {
                        'field': 'namespace',
                        'old_value': '',
                        'new_value': 'test'
                    },
                    {
                        'field': 'homepage_url',
                        'old_value': None,
                        'new_value': 'https://example.com'
                    }
                ]
            }
        }
        history_entry = p1.history[0]
        history_entry.pop('timestamp')
        self.assertEqual(expected_history_entry, history_entry)

    def test_packagedb_package_model_update_fields_special_cases(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        # Test dates
        date_fields = [
            'created_date',
            'last_indexed_date',
            'release_date',
        ]
        for field in date_fields:
            value = getattr(p1, field)
            self.assertEqual(None, value)
        timestamp_str = '2017-03-25T14:39:00+00:00'
        package, updated_fields = p1.update_fields(
            **{field: timestamp_str for field in date_fields}
        )
        timestamp = dateutil_parse(timestamp_str)
        for field in date_fields:
            value = getattr(package, field)
            self.assertEqual(timestamp, value)
        self.assertEqual(
            sorted(updated_fields),
            sorted(date_fields + ['history'])
        )

        # Test qualifiers
        self.assertEqual('', p1.qualifiers)
        dict_qualifiers1 = {
            'classifier': 'sources',
            'type': 'war',
        }
        string_qualifiers1='classifier=sources&type=war'
        package, updated_fields = p1.update_field('qualifiers', dict_qualifiers1)
        self.assertEqual(
            sorted(['qualifiers', 'history']),
            sorted(updated_fields),
        )
        self.assertEqual(
            string_qualifiers1,
            p1.qualifiers
        )
        string_qualifiers2='classifier=somethingelse'
        package, updated_fields = p1.update_field('qualifiers', string_qualifiers2)
        self.assertEqual(
            sorted(['qualifiers', 'history']),
            sorted(updated_fields),
        )
        self.assertEqual(
            string_qualifiers2,
            p1.qualifiers,
        )
        expected_history = [
            {
                'message': 'Package field values have been updated.',
                'data': {
                    'updated_fields': [
                        {
                            'field': 'created_date',
                            'old_value': 'None',
                            'new_value': '2017-03-25 14:39:00+00:00'
                        }, {
                            'field': 'last_indexed_date',
                            'old_value': 'None',
                            'new_value': '2017-03-25 14:39:00+00:00'
                        }, {
                            'field': 'release_date',
                            'old_value': 'None',
                            'new_value': '2017-03-25 14:39:00+00:00'
                        }
                    ]
                }
            },
            {
                'message': 'Package field values have been updated.',
                'data': {
                    'updated_fields': [
                        {
                            'field': 'qualifiers',
                            'old_value': '',
                            'new_value': 'classifier=sources&type=war'
                        }
                    ]
                }
            },
            {
                'message': 'Package field values have been updated.',
                'data': {
                    'updated_fields': [
                        {
                            'field': 'qualifiers',
                            'old_value': 'classifier=sources&type=war',
                            'new_value': 'classifier=somethingelse'
                        }
                    ]
                }
            }
        ]
        # remove timestamp before comparison
        history = []
        for entry in p1.history:
            entry.pop('timestamp')
            history.append(entry)
        self.assertEquals(expected_history, history)
