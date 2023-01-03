#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

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

    def test_package_creation(self):
        test_package = Package.objects.get(download_url=self.created_package_download_url)
        self.assertIsNotNone(test_package)
        for key, val in self.created_package_data.items():
            self.assertEqual(val.lower(), getattr(test_package, key))

    def test_package_insertion(self):
        test_package = Package.objects.get(download_url=self.inserted_package_download_url)
        self.assertIsNotNone(test_package)
        for key, val in self.inserted_package_data.items():
            self.assertEqual(val.lower(), getattr(test_package, key))

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
