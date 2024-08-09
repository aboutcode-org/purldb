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

from packagedb.models import DependentPackage, PackageWatch
from packagedb.models import Package
from packagedb.models import Party
from packagedb.models import Resource

from unittest.mock import patch


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

    def test_packagedb_package_model_update_fields(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        self.assertFalse(p1.history)
        self.assertEqual('', p1.namespace)
        self.assertEqual(None, p1.homepage_url)
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
        package, updated_fields = p1.update_fields(qualifiers=dict_qualifiers1)
        self.assertEqual(
            sorted(['qualifiers', 'history']),
            sorted(updated_fields),
        )
        self.assertEqual(
            string_qualifiers1,
            p1.qualifiers
        )
        string_qualifiers2='classifier=somethingelse'
        package, updated_fields = p1.update_fields(qualifiers=string_qualifiers2)
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
        self.assertEqual(expected_history, history)

    def test_packagedb_package_model_update_fields_related_models(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        path = 'asdf'
        resources = [Resource(package=p1, path=path)]
        _, updated_fields = p1.update_fields(resources=resources)
        self.assertEqual(
            sorted(['resources', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'resources' with 1 new entries."
        self.assertEqual(1, len(p1.history))
        history_message = p1.history[0]['message']
        self.assertEqual(expected_message, history_message)

        p2 = Package.objects.create(download_url='http://b.b', name='example', version='1.0')
        resources = [
            {
                "path": "example.jar",
                "type": "file",
                "name": "example.jar",
                "status": "",
                "tag": "",
                "extension": ".jar",
                "size": 20621,
                "md5": "9307296944793049edbef60784afb12d",
                "sha1": "6f776af78d7eded5a1eb2870f9d81abbf690f8b8",
                "sha256": "bb83934ba50c26c093d4bea5f3faead15a3e8c176dc5ec93837d6beeaa1f27e8",
                "sha512": "",
                "mime_type": "application/java-archive",
                "file_type": "Java archive data (JAR)",
                "programming_language": "",
                "is_binary": True,
                "is_text": False,
                "is_archive": True,
                "is_media": False,
                "is_key_file": True,
                "detected_license_expression": "",
                "detected_license_expression_spdx": "",
                "license_detections": [],
                "license_clues": [],
                "percentage_of_license_text": 0.0,
                "compliance_alert": "",
                "copyrights": [],
                "holders": [],
                "authors": [],
                "package_data": [],
                "for_packages": [

                ],
                "emails": [],
                "urls": [],
                "extra_data": {}
            }
        ]
        _, updated_fields = p2.update_fields(resources=resources)
        self.assertEqual(
            sorted(['resources', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'resources' with 1 new entries."
        self.assertEqual(1, len(p2.history))
        history_message = p2.history[0]['message']
        self.assertEqual(expected_message, history_message)

        p3 = Package.objects.create(download_url='http://foo', name='foo', version='1.0')
        parties = [
             dict(
                type='admin',
                role='admin',
                name='foo',
                email='foo@foo.com',
                url='foo.com',
             )
        ]
        _, updated_fields = p3.update_fields(parties=parties)
        self.assertEqual(
            sorted(['parties', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'parties' with 1 new entries."
        self.assertEqual(1, len(p3.history))
        history_message = p3.history[0]['message']
        self.assertEqual(expected_message, history_message)

        p4 = Package.objects.create(download_url='http://bar', name='bar', version='1.0')
        parties = [
             Party(
                package=p4,
                type='admin',
                role='admin',
                name='bar',
                email='bar@bar.com',
                url='foo.com',
             )
        ]
        _, updated_fields = p4.update_fields(parties=parties)
        self.assertEqual(
            sorted(['parties', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'parties' with 1 new entries."
        self.assertEqual(1, len(p4.history))
        history_message = p4.history[0]['message']
        self.assertEqual(expected_message, history_message)

        p5 = Package.objects.create(download_url='http://baz', name='baz', version='1.0')
        dependencies = [
            dict(
                purl='pkg:baz_dep@1.0',
                extracted_requirement='>1',
                scope='runtime',
                is_runtime=True,
                is_optional=False,
                is_resolved=True,
            )
        ]
        _, updated_fields = p5.update_fields(dependencies=dependencies)
        self.assertEqual(
            sorted(['dependencies', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'dependencies' with 1 new entries."
        self.assertEqual(1, len(p5.history))
        history_message = p5.history[0]['message']
        self.assertEqual(expected_message, history_message)

        p6 = Package.objects.create(download_url='http://qux', name='qux', version='1.0')
        dependencies = [
            DependentPackage(
                package=p6,
                purl='pkg:qux_dep@1.0',
                extracted_requirement='>1',
                scope='runtime',
                is_runtime=True,
                is_optional=False,
                is_resolved=True,
            )
        ]
        _, updated_fields = p6.update_fields(dependencies=dependencies)
        self.assertEqual(
            sorted(['dependencies', 'history']),
            sorted(updated_fields)
        )
        expected_message = "Replaced 0 existing entries of field 'dependencies' with 1 new entries."
        self.assertEqual(1, len(p6.history))
        history_message = p6.history[0]['message']
        self.assertEqual(expected_message, history_message)

    def test_packagedb_package_model_update_fields_exceptions(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        with self.assertRaises(AttributeError):
            p1.update_fields(asdf=123)

        with self.assertRaises(ValueError):
            p1.update_fields(resources=[1])

        with self.assertRaises(ValueError):
            p1.update_fields(dependencies=[1])

        with self.assertRaises(ValueError):
            p1.update_fields(parties=[1])


class PackageWatchModelTestCase(TransactionTestCase):
    @patch("packagedb.models.PackageWatch.create_new_job")
    def setUp(self, mock_create_new_job):
        mock_create_new_job.return_value = None

        self.package_watch1 = PackageWatch.objects.create(
            package_url="pkg:maven/org.test/test-package"
        )

        self.package_watch2 = PackageWatch.objects.create(
            package_url="pkg:maven/org.test/test-package2"
        )

    def test_package_watch_no_duplicate(self):
        self.assertRaises(
            IntegrityError,
            PackageWatch.objects.create,
            package_url="pkg:maven/org.test/test-package",
        )

    def test_package_watch_immutable_fields(self):
        self.package_watch1.type = "npm"
        self.assertRaises(ValueError, self.package_watch1.save)

        self.package_watch1.namespace = "org.test1"
        self.assertRaises(ValueError, self.package_watch1.save)

        self.package_watch1.name = "new"
        self.assertRaises(ValueError, self.package_watch1.save)

    @patch("packagedb.models.PackageWatch.create_new_job")
    def test_package_watch_mutable_fields(self, mock_create_new_job):
        mock_create_new_job.return_value = None

        self.package_watch1.is_active = False
        self.package_watch1.save()
        self.assertEqual(False, self.package_watch1.is_active)

        self.package_watch1.watch_interval = 1
        self.package_watch1.save()
        self.assertEqual(1, self.package_watch1.watch_interval)

        self.package_watch1.watch_error = "error"
        self.package_watch1.save()
        self.assertEqual("error", self.package_watch1.watch_error)

    @patch("packagedb.models.PackageWatch.create_new_job")
    def test_package_watch_reschedule_on_modification(self, mock_create_new_job):
        mock_create_new_job.side_effect = ["reschedule_id_new_interval", None]

        self.package_watch1.watch_interval = 1
        self.package_watch1.save()
        self.assertEqual("reschedule_id_new_interval", self.package_watch1.schedule_work_id)

        self.package_watch1.is_active = False
        self.package_watch1.save()
        self.assertEqual(None, self.package_watch1.schedule_work_id)



    def test_get_or_none(self):
        Package.objects.create(download_url='http://a.ab', name='name', version='1.0', type="foo")
        package = Package.objects.filter(
            download_url="http://a.ab"
        ).get_or_none()
        assert package
        assert Package.objects.filter(
            download_url="http://a.ab-foobar"
        ).get_or_none() == None
