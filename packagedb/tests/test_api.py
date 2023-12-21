#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from uuid import uuid4
import json
import os

from django.contrib.postgres.search import SearchVector
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from minecode.models import PriorityResourceURI
from minecode.models import ScannableURI
from minecode.utils_test import JsonBasedTesting
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet
from packagedb.models import Resource

from unittest import mock
from univers.versions import MavenVersion

class ResourceAPITestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://test-url.com/package1.tar.gz',
            type='type1',
            name='name1',
        )

        self.package2 = Package.objects.create(
            download_url='https://test-url.com/package2.tar.gz',
            type='type2',
            name='name2',
        )

        self.resource1 = Resource.objects.create(
            package=self.package1,
            path='package1/contents1.txt',
            size=101,
            sha1='testsha11',
            md5='testmd51',
            sha256='testsha2561',
            sha512='testsha5121',
            git_sha1='testgit_sha11',
            is_file=True,
            extra_data=json.dumps({'test1': 'data1'})
        )

        self.resource2 = Resource.objects.create(
            package=self.package2,
            path='package2/contents2.txt',
            size=102,
            sha1='testsha12',
            md5='testmd52',
            sha256='testsha2562',
            sha512='testsha5122',
            git_sha1='testgit_sha12',
            is_file=True,
            extra_data=json.dumps({'test2': 'data2'})
        )

        self.test_url = 'http://testserver/api/packages/{}/'

        self.client = APIClient()

    def test_api_resource_list_endpoint(self):
        response = self.client.get('/api/resources/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

    def test_api_resource_retrieve_endpoint(self):
        response = self.client.get('/api/resources/{}/'.format(self.resource1.sha1))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('package'), self.test_url.format(str(self.package1.uuid)))
        self.assertEqual(response.data.get('purl'), self.package1.package_url)
        self.assertEqual(response.data.get('path'), self.resource1.path)
        self.assertEqual(response.data.get('size'), self.resource1.size)
        self.assertEqual(response.data.get('sha1'), self.resource1.sha1)
        self.assertEqual(response.data.get('md5'), self.resource1.md5)
        self.assertEqual(response.data.get('sha256'), self.resource1.sha256)
        self.assertEqual(response.data.get('sha512'), self.resource1.sha512)
        self.assertEqual(response.data.get('git_sha1'), self.resource1.git_sha1)
        self.assertEqual(response.data.get('extra_data'), self.resource1.extra_data)
        self.assertEqual(response.data.get('type'), self.resource1.type)

    def test_api_resource_list_endpoint_returns_none_when_filtering_by_non_uuid_value(self):
        response = self.client.get('/api/resources/?package={}'.format('not-a-uuid'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))

    def test_api_resource_list_endpoint_returns_none_when_filtering_by_wrong_uuid(self):
        response = self.client.get('/api/resources/?package={}'.format('4eb22e66-3e1c-4818-9b5e-858008a7c2b5'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))

    def test_api_resource_list_endpoint_returns_none_when_filtering_by_blank_uuid(self):
        response = self.client.get('/api/resources/?package={}'.format(''))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

    def test_api_resource_list_endpoint_filters_by_package1_uuid(self):
        response = self.client.get('/api/resources/?package={}'.format(self.package1.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_resource = response.data.get('results')[0]
        self.assertEqual(test_resource.get('package'), self.test_url.format(str(self.package1.uuid)))
        self.assertEqual(test_resource.get('purl'), self.package1.package_url)
        self.assertEqual(test_resource.get('path'), self.resource1.path)
        self.assertEqual(test_resource.get('size'), self.resource1.size)
        self.assertEqual(test_resource.get('sha1'), self.resource1.sha1)
        self.assertEqual(test_resource.get('md5'), self.resource1.md5)
        self.assertEqual(test_resource.get('sha256'), self.resource1.sha256)
        self.assertEqual(test_resource.get('sha512'), self.resource1.sha512)
        self.assertEqual(test_resource.get('git_sha1'), self.resource1.git_sha1)
        self.assertEqual(test_resource.get('extra_data'), self.resource1.extra_data)
        self.assertEqual(test_resource.get('type'), self.resource1.type)

    def test_api_resource_list_endpoint_filters_by_package2_uuid(self):
        response = self.client.get('/api/resources/?package={}'.format(self.package2.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_resource = response.data.get('results')[0]
        self.assertEqual(test_resource.get('package'), self.test_url.format(str(self.package2.uuid)))
        self.assertEqual(test_resource.get('purl'), self.package2.package_url)
        self.assertEqual(test_resource.get('path'), self.resource2.path)
        self.assertEqual(test_resource.get('size'), self.resource2.size)
        self.assertEqual(test_resource.get('sha1'), self.resource2.sha1)
        self.assertEqual(test_resource.get('md5'), self.resource2.md5)
        self.assertEqual(test_resource.get('sha256'), self.resource2.sha256)
        self.assertEqual(test_resource.get('sha512'), self.resource2.sha512)
        self.assertEqual(test_resource.get('git_sha1'), self.resource2.git_sha1)
        self.assertEqual(test_resource.get('extra_data'), self.resource2.extra_data)
        self.assertEqual(test_resource.get('type'), self.resource2.type)

    def test_api_resource_list_endpoint_returns_none_when_filtering_by_wrong_purl(self):
        response = self.client.get('/api/resources/?purl={}'.format('pkg:npm/test@1.0.0'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))

    def test_api_resource_list_endpoint_returns_none_when_filtering_by_blank_uuid(self):
        response = self.client.get('/api/resources/?purl={}'.format(''))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

    def test_api_resource_list_endpoint_filters_by_package1_purl(self):
        response = self.client.get('/api/resources/?purl={}'.format(self.package1.package_url))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_resource = response.data.get('results')[0]
        self.assertEqual(test_resource.get('package'), self.test_url.format(str(self.package1.uuid)))
        self.assertEqual(test_resource.get('purl'), self.package1.package_url)
        self.assertEqual(test_resource.get('path'), self.resource1.path)
        self.assertEqual(test_resource.get('size'), self.resource1.size)
        self.assertEqual(test_resource.get('sha1'), self.resource1.sha1)
        self.assertEqual(test_resource.get('md5'), self.resource1.md5)
        self.assertEqual(test_resource.get('sha256'), self.resource1.sha256)
        self.assertEqual(test_resource.get('sha512'), self.resource1.sha512)
        self.assertEqual(test_resource.get('git_sha1'), self.resource1.git_sha1)
        self.assertEqual(test_resource.get('extra_data'), self.resource1.extra_data)
        self.assertEqual(test_resource.get('type'), self.resource1.type)

    def test_api_resource_list_endpoint_filters_by_package2_purl(self):
        response = self.client.get('/api/resources/?purl={}'.format(self.package2.package_url))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_resource = response.data.get('results')[0]
        self.assertEqual(test_resource.get('package'), self.test_url.format(str(self.package2.uuid)))
        self.assertEqual(test_resource.get('purl'), self.package2.package_url)
        self.assertEqual(test_resource.get('path'), self.resource2.path)
        self.assertEqual(test_resource.get('size'), self.resource2.size)
        self.assertEqual(test_resource.get('sha1'), self.resource2.sha1)
        self.assertEqual(test_resource.get('md5'), self.resource2.md5)
        self.assertEqual(test_resource.get('sha256'), self.resource2.sha256)
        self.assertEqual(test_resource.get('sha512'), self.resource2.sha512)
        self.assertEqual(test_resource.get('git_sha1'), self.resource2.git_sha1)
        self.assertEqual(test_resource.get('extra_data'), self.resource2.extra_data)
        self.assertEqual(test_resource.get('type'), self.resource2.type)

    def test_api_resource_filter_by_checksums(self):
        sha1s = [
            'testsha11',
            'testsha12',
        ]
        data = {
            'sha1': sha1s
        }
        response = self.client.post('/api/resources/filter_by_checksums/', data=data)
        self.assertEqual(2, response.data['count'])
        expected = self.get_test_loc('api/resource-filter_by_checksums-expected.json')
        self.check_expected_results(response.data['results'], expected, fields_to_remove=["url", "uuid", "package"], regen=False)

class PackageApiTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):

        self.package_data = {
            'type': 'generic',
            'namespace': 'generic',
            'name': 'Foo',
            'version': '12.34',
            'qualifiers': 'test_qual=qual',
            'subpath': 'test_subpath',
            'download_url': 'http://example.com',
            'filename': 'Foo.zip',
            'sha1': 'testsha1',
            'md5': 'testmd5',
            'size': 101,
        }

        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()

        self.package.append_to_history('test-message')
        self.package.save()

        self.package_data2 = {
            'type': 'npm',
            'namespace': 'example',
            'name': 'Bar',
            'version': '56.78',
            'qualifiers': '',
            'subpath': '',
            'download_url': 'http://somethingelse.org',
            'filename': 'Bar.zip',
            'sha1': 'testsha1-2',
            'md5': 'testmd5-2',
            'size': 100,
        }
        self.package2 = Package.objects.create(**self.package_data2)
        self.package2.refresh_from_db()

        self.package_data3 = {
            'type': 'jar',
            'namespace': 'sample',
            'name': 'Baz',
            'version': '90.12',
            'qualifiers': '',
            'subpath': '',
            'download_url': 'http://anotherexample.com',
            'filename': 'Baz.zip',
            'sha1': 'testsha1-3',
            'md5': 'testmd5-3',
            'size': 100,
        }
        self.package3 = Package.objects.create(**self.package_data3)
        self.package3.refresh_from_db()

        self.package_data4= {
            'type': 'jar',
            'namespace': 'sample',
            'name': 'Baz',
            'version': '90.123',
            'qualifiers': '',
            'subpath': '',
            'download_url': 'http://anothersample.com',
            'filename': 'Baz.zip',
            'sha1': 'testsha1-4',
            'md5': 'testmd5-3',
            'size': 100,
            'package_content': PackageContentType.BINARY,
        }
        self.package4 = Package.objects.create(**self.package_data4)
        self.package4.refresh_from_db()

        self.package_data5= {
            'type': 'maven',
            'namespace': 'foot',
            'name': 'baz',
            'version': '90.123',
            'qualifiers': 'classifier=source',
            'subpath': '',
            'download_url': 'http://test-maven.com',
            'filename': 'Baz.zip',
            'sha1': 'testsha1-5',
            'md5': 'testmd5-11',
            'size': 100,
            'package_content': PackageContentType.SOURCE_ARCHIVE,
            'declared_license_expression': 'MIT',
        }

        self.package5 = Package.objects.create(**self.package_data5)
        self.package5.refresh_from_db()

        self.package_data6= {
            'type': 'maven',
            'namespace': 'fooo',
            'name': 'baz',
            'version': '90.123',
            'qualifiers': '',
            'subpath': '',
            'download_url': 'http://test-maven-11.com',
            'filename': 'Baz.zip',
            'sha1': 'testsha1-6',
            'md5': 'testmd5-11',
            'size': 100,
            'package_content': PackageContentType.BINARY,
        }

        self.package6 = Package.objects.create(**self.package_data6)
        self.package6.refresh_from_db()

        self.package_data7= {
            'type': 'github',
            'namespace': 'glue',
            'name': 'cat',
            'version': '90.123',
            'qualifiers': '',
            'subpath': '',
            'download_url': 'http://test-maven-111.com',
            'filename': 'Baz.zip',
            'sha1': 'testsha1-7',
            'md5': 'testmd5-11',
            'size': 100,
            'copyright': 'BACC',
            'package_content': PackageContentType.SOURCE_REPO,
        }

        self.package7 = Package.objects.create(**self.package_data7)
        self.package7.refresh_from_db()

        self.packageset_1 = PackageSet.objects.create()
        self.packageset_1.packages.add(self.package6)
        self.packageset_1.packages.add(self.package5)
        self.packageset_1.packages.add(self.package7)

        self.test_url = 'http://testserver/api/packages/{}/'

        self.client = APIClient()

    def test_package_api_list_endpoint(self):
        response = self.client.get('/api/packages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(7, response.data.get('count'))

    def test_package_api_list_endpoint_filter(self):
        for key, value in self.package_data.items():
            response = self.client.get('/api/packages/?{}={}'.format(key, value))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

    def test_package_api_list_endpoint_filter_by_purl_fields_ignores_case(self):
        for key, value in self.package_data.items():
            # Skip non-purl fields
            if key not in ['type', 'namespace', 'name']:
                continue

            response = self.client.get('/api/packages/?{}={}'.format(key, value.lower()))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

            response = self.client.get('/api/packages/?{}={}'.format(key, value.upper()))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

    def test_package_api_list_endpoint_search(self):
        # Create a dummy package to verify search filter works.
        Package.objects.create(
            type='generic',
            namespace='dummy-namespace',
            name='dummy-name',
            version='12.35',
            download_url='https://dummy.com/dummy'
        )

        response = self.client.get('/api/packages/?search={}'.format('generic'))
        assert response.data.get('count') == 2
        response = self.client.get('/api/packages/?search={}'.format('dummy'))
        assert response.data.get('count') == 1
        response = self.client.get('/api/packages/?search={}'.format('DUMMY'))
        assert response.data.get('count') == 1
        response = self.client.get('/api/packages/?search={}'.format('12.35'))
        assert response.data.get('count') == 1
        response = self.client.get('/api/packages/?search={}'.format('https://dummy.com/dummy'))
        assert response.data.get('count') == 1

    def test_package_api_retrieve_endpoint(self):
        response = self.client.get('/api/packages/{}/'.format(self.package.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key, value in response.data.items():
            # Handle the API-only `url` key
            if key == 'url':
                self.assertEqual(value, self.test_url.format(str(self.package.uuid)))
                continue

            if key in ['type', 'namespace', 'name', 'version', 'qualifiers', 'subpath']:
                self.assertEqual(value, getattr(self.package, key))
                continue

            if key == 'history':
                self.assertIn('test-message', value)

            self.assertTrue(hasattr(self.package, key))
            if key in self.package_data.keys():
                self.assertEqual(value, getattr(self.package, key))

    def test_api_package_latest_version_action(self):
        p1 = Package.objects.create(download_url='http://a.a', type='generic', name='name', version='1.0')
        p2 = Package.objects.create(download_url='http://b.b', type='generic', name='name', version='2.0')
        p3 = Package.objects.create(download_url='http://c.c', type='generic', name='name', version='3.0')

        response = self.client.get(reverse('api:package-latest-version', args=[p1.uuid]))
        self.assertEqual('3.0', response.data['version'])

        response = self.client.get(reverse('api:package-latest-version', args=[p2.uuid]))
        self.assertEqual('3.0', response.data['version'])

        response = self.client.get(reverse('api:package-latest-version', args=[p3.uuid]))
        self.assertEqual('3.0', response.data['version'])

    def test_api_package_resources_action(self):
        # create 10 resources
        for i in range(0, 10):
            Resource.objects.create(package=self.package, path='path{}/'.format(i))

        response = self.client.get(reverse('api:package-resources', args=[self.package.uuid]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(10, response.data['count'])

        for result, i in zip(response.data['results'], range(0, 10)):
            self.assertEqual(result.get('path'), 'path{}/'.format(i))

    def test_api_package_list_endpoint_multiple_char_filters(self):
        filters = f'?md5={self.package.md5}&md5={self.package2.md5}'
        response = self.client.get(f'/api/packages/{filters}')
        self.assertEqual(2, response.data['count'])
        purls = [result.get('purl') for result in response.data['results']]
        self.assertIn(self.package.purl, purls)
        self.assertIn(self.package2.purl, purls)
        self.assertNotIn(self.package3.purl, purls)

        filters = f'?sha1={self.package2.sha1}&sha1={self.package3.sha1}'
        response = self.client.get(f'/api/packages/{filters}')
        self.assertEqual(2, response.data["count"])
        purls = [result.get('purl') for result in response.data['results']]
        self.assertIn(self.package2.purl, purls)
        self.assertIn(self.package3.purl, purls)
        self.assertNotIn(self.package.purl, purls)


    def test_package_api_filter_by_checksums(self):
        sha1s = [
            'testsha1',
            'testsha1-2',
            'testsha1-3',
            'testsha1-4',
            'testsha1-6',
        ]
        data = {
            'sha1': sha1s,
        }
        response = self.client.post('/api/packages/filter_by_checksums/', data=data)
        self.assertEqual(5, response.data['count'])
        expected = self.get_test_loc('api/package-filter_by_checksums-expected.json')
        self.check_expected_results(response.data['results'], expected, fields_to_remove=["url", "uuid", "resources", "package_sets",], regen=False)
        data["enhance_package_data"] = True
        enhanced_response = self.client.post('/api/packages/filter_by_checksums/', data=data)
        self.assertEqual(5, len(enhanced_response.data['results']))
        expected = self.get_test_loc('api/package-filter_by_checksums-enhanced-package-data-expected.json')
        self.check_expected_results(enhanced_response.data['results'], expected, fields_to_remove=["url", "uuid", "resources", "package_sets",], regen=False)


class PackageApiReindexingTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        package_download_url = 'http://anotherexample.com'
        self.package_data = {
            'type': 'maven',
            'namespace': 'sample',
            'name': 'Baz',
            'version': '90.12',
            'qualifiers': '',
            'subpath': '',
            'download_url': package_download_url,
            'filename': 'Baz.zip',
            'sha1': 'testsha1-3',
            'md5': 'testmd5-3',
            'size': 100,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()
        self.scannableuri = ScannableURI.objects.create(
            package=self.package,
            uri=package_download_url,
        )
        self.scannableuri.scan_status = ScannableURI.SCAN_INDEXED
        self.scan_uuid = uuid4()
        self.scannableuri.scan_uuid = self.scan_uuid
        self.scannableuri.scan_error = 'error'
        self.scannableuri.index_error = 'error'
        self.scan_request_date = timezone.now()
        self.scannableuri.scan_request_date = self.scan_request_date

    def test_reindex_package(self):
        self.assertEqual(False, self.scannableuri.rescan_uri)
        self.assertEqual(0, self.scannableuri.priority)
        self.assertEqual(self.scan_uuid, self.scannableuri.scan_uuid)
        self.assertEqual('error', self.scannableuri.scan_error)
        self.assertEqual('error', self.scannableuri.index_error)
        self.assertEqual(self.scan_request_date, self.scannableuri.scan_request_date)
        response = self.client.get(f'/api/packages/{self.package.uuid}/reindex_package/')
        self.assertEqual('pkg:maven/sample/Baz@90.12 has been queued for reindexing', response.data['status'])
        self.scannableuri.refresh_from_db()
        self.assertEqual(True, self.scannableuri.rescan_uri)
        self.assertEqual(100, self.scannableuri.priority)
        self.assertEqual(None, self.scannableuri.scan_uuid)
        self.assertEqual(None, self.scannableuri.scan_error)
        self.assertEqual(None, self.scannableuri.index_error)
        self.assertEqual(None, self.scannableuri.scan_request_date)


class PackageApiPurlFilterTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package_data1 = {
            'type': 'maven',
            'namespace': 'org.apache.commons',
            'name': 'io',
            'version': '1.3.4',
            'download_url': 'http://example1.com',
            'extra_data': json.dumps({'test2': 'data2'})
        }

        self.package_data2 = {
            'type': 'maven',
            'namespace': 'org.apache.commons',
            'name': 'io',
            'version': '2.3.4',
            'download_url': 'http://example2.com',
            'extra_data': json.dumps({'test2': 'data2'})
        }

        self.package_data3 = {
            'type': 'maven',
            'namespace': '',
            'name': 'test',
            'version': '1.0.0',
            'qualifiers':'',
            'package_content': PackageContentType.BINARY,
            'download_url': 'https://example.com/test-1.0.0.jar',
        }

        self.package_data4 = {
            'type': 'maven',
            'namespace': '',
            'name': 'test',
            'version': '1.0.0',
            'qualifiers':'classifier=sources',
            'declared_license_expression': 'apache-2.0',
            'copyright': 'Copyright (c) example corp.',
            'holder': 'example corp.',
            'package_content': PackageContentType.SOURCE_ARCHIVE,
            'download_url': 'https://example.com/test-1.0.0-sources.jar',
        }

        self.package1 = Package.objects.create(**self.package_data1)
        self.package2 = Package.objects.create(**self.package_data2)
        self.package3 = Package.objects.create(**self.package_data3)
        self.package4 = Package.objects.create(**self.package_data4)

        self.purl1 = self.package1.package_url
        self.purl2 = self.package2.package_url

        self.missing_purl = 'pkg:PYPI/Django_package@1.11.1.dev1'

        self.package_set1 = PackageSet.objects.create()
        self.package_set1.add_to_package_set(self.package1)
        self.package_set1.add_to_package_set(self.package2)

        self.package_set2 = PackageSet.objects.create()
        self.package_set2.add_to_package_set(self.package3)
        self.package_set2.add_to_package_set(self.package4)

        self.client = APIClient()

    def tearDown(self):
        Package.objects.all().delete()

    def test_package_api_purl_filter_by_query_param_invalid_purl(self):
        response = self.client.get('/api/packages/?purl={}'.format('11111'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))

    def test_package_api_purl_filter_by_query_param_no_value(self):
        response = self.client.get('/api/packages/?purl={}'.format(''))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(4, response.data.get('count'))

    def test_package_api_purl_filter_by_query_param_non_existant_purl(self):
        response = self.client.get('/api/packages/?purl={}'.format(self.missing_purl))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))

    def test_package_api_purl_filter_by_query_param_no_version(self):
        response = self.client.get('/api/packages/?purl={}'.format('pkg:maven/org.apache.commons/io'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

    def test_package_api_purl_filter_by_query_param1(self):
        response = self.client.get('/api/packages/?purl={}'.format(self.purl1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_package = response.data.get('results')[0]
        self.assertEqual(test_package.get('type'), self.package_data1.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data1.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data1.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data1.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data1.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data1.get('extra_data'))

    def test_package_api_purl_filter_by_query_param2(self):
        response = self.client.get('/api/packages/?purl={}'.format(self.purl2))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_package = response.data.get('results')[0]
        self.assertEqual(test_package.get('type'), self.package_data2.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data2.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data2.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data2.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data2.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data2.get('extra_data'))

    def test_package_api_purl_filter_by_both_query_params(self):
        response = self.client.get('/api/packages/?purl={}&purl={}'.format(self.purl1, self.purl2))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

        test_package = response.data.get('results')[0]
        self.assertEqual(test_package.get('type'), self.package_data1.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data1.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data1.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data1.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data1.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data1.get('extra_data'))

        test_package = response.data.get('results')[1]
        self.assertEqual(test_package.get('type'), self.package_data2.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data2.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data2.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data2.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data2.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data2.get('extra_data'))

    def test_package_api_purl_filter_by_two_purl_values_on_multiple_packages(self):
        extra_test_package = Package.objects.create(
            download_url='https://extra-pkg.com/download',
            type='generic',
            name='extra-name',
            version='2.2.2'
        )

        response = self.client.get('/api/packages/?purl={}&purl={}'.format(self.purl1, self.purl2))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data.get('count'))

        test_package = response.data.get('results')[0]
        self.assertEqual(test_package.get('type'), self.package_data1.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data1.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data1.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data1.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data1.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data1.get('extra_data'))

        test_package = response.data.get('results')[1]
        self.assertEqual(test_package.get('type'), self.package_data2.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data2.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data2.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data2.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data2.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data2.get('extra_data'))

    def test_package_api_purl_filter_by_one_purl_multiple_params(self):
        response = self.client.get('/api/packages/?purl={}&purl={}'.format(self.purl1, self.missing_purl))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

        test_package = response.data.get('results')[0]
        self.assertEqual(test_package.get('type'), self.package_data1.get('type'))
        self.assertEqual(test_package.get('namespace'), self.package_data1.get('namespace'))
        self.assertEqual(test_package.get('name'), self.package_data1.get('name'))
        self.assertEqual(test_package.get('version'), self.package_data1.get('version'))
        self.assertEqual(test_package.get('download_url'), self.package_data1.get('download_url'))
        self.assertEqual(test_package.get('extra_data'), self.package_data1.get('extra_data'))

    def test_package_api_purl_filter_by_multiple_blank_purl(self):
        response = self.client.get('/api/packages/?purl={}&purl={}'.format('', ''))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(4, response.data.get('count'))

    def test_package_api_get_enhanced_package(self):
        response = self.client.get(reverse('api:package-get-enhanced-package-data', args=[self.package3.uuid]))
        result = response.data
        expected = self.get_test_loc('api/enhanced_package.json')
        self.check_expected_results(result, expected, fields_to_remove=['package_sets'], regen=False)

class CollectApiTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        package_download_url = 'http://anotherexample.com'
        self.package_data = {
            'type': 'maven',
            'namespace': 'sample',
            'name': 'Baz',
            'version': '90.12',
            'qualifiers': '',
            'subpath': '',
            'download_url': package_download_url,
            'filename': 'Baz.zip',
            'sha1': 'testsha1-3',
            'md5': 'testmd5-3',
            'size': 100,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()
        self.scannableuri = ScannableURI.objects.create(
            package=self.package,
            uri=package_download_url,
        )
        self.scannableuri.scan_status = ScannableURI.SCAN_INDEXED
        self.scan_uuid = uuid4()
        self.scannableuri.scan_uuid = self.scan_uuid
        self.scannableuri.scan_error = 'error'
        self.scannableuri.index_error = 'error'
        self.scan_request_date = timezone.now()
        self.scannableuri.scan_request_date = self.scan_request_date

        package_download_url2 = 'http://somethingelse.org'
        self.package_data2 = {
            'type': 'npm',
            'namespace': 'example',
            'name': 'bar',
            'version': '56.78',
            'qualifiers': '',
            'subpath': '',
            'download_url': package_download_url2,
            'filename': 'Bar.zip',
            'sha1': 'testsha1-2',
            'md5': 'testmd5-2',
            'size': 100,
        }
        self.package2 = Package.objects.create(**self.package_data2)
        self.package2.refresh_from_db()
        self.scannableuri2 = ScannableURI.objects.create(
            package=self.package2,
            uri=package_download_url2,
        )
        self.scannableuri2.scan_status = ScannableURI.SCAN_INDEXED
        self.scan_uuid2 = uuid4()
        self.scannableuri2.scan_uuid = self.scan_uuid2
        self.scannableuri2.scan_error = 'error'
        self.scannableuri2.index_error = 'error'
        self.scan_request_date2 = timezone.now()
        self.scannableuri2.scan_request_date = self.scan_request_date2
    
    def test_package_live(self):
        purl_str = 'pkg:maven/org.apache.twill/twill-core@0.12.0'
        download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0.jar'
        purl_sources_str = f'{purl_str}?classifier=sources'
        sources_download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0-sources.jar'

        self.assertEqual(0, Package.objects.filter(download_url=download_url).count())
        self.assertEqual(0, Package.objects.filter(download_url=sources_download_url).count())
        response = self.client.get(f'/api/collect/?purl={purl_str}')
        self.assertEqual(1, Package.objects.filter(download_url=download_url).count())
        self.assertEqual(1, Package.objects.filter(download_url=sources_download_url).count())
        expected = self.get_test_loc('api/twill-core-0.12.0.json')

        self.assertEqual(2, len(response.data))
        result = response.data[0]

        # remove fields
        result.pop('url')
        fields_to_remove = [
            'uuid',
            'resources',
            'package_sets',
        ]

        self.check_expected_results(result, expected, fields_to_remove=fields_to_remove, regen=False)
    
    def test_package_api_index_packages_endpoint(self):
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(0, priority_resource_uris_count)
        packages = [
            {'purl':'pkg:maven/ch.qos.reload4j/reload4j@1.2.24'},
            {'purl':'pkg:maven/com.esotericsoftware.kryo/kryo@2.24.0'},
            {'purl':'pkg:bitbucket/example/example@1.0.0'},
        ]
        data = {
            'packages': packages
        }
        response = self.client.post('/api/collect/index_packages/', data=data, content_type="application/json")
        self.assertEqual(2, response.data['queued_packages_count'])
        expected_queued_packages = [
            'pkg:maven/ch.qos.reload4j/reload4j@1.2.24',
            'pkg:maven/com.esotericsoftware.kryo/kryo@2.24.0',
        ]
        self.assertEqual(
            sorted(expected_queued_packages),
            sorted(response.data['queued_packages'])
        )
        self.assertEqual(0, response.data['unqueued_packages_count'])
        self.assertEqual([], response.data['unqueued_packages'])
        self.assertEqual(1, response.data['unsupported_packages_count'])
        expected_unsupported_packages = [
            'pkg:bitbucket/example/example@1.0.0'
        ]
        self.assertEqual(expected_unsupported_packages, response.data['unsupported_packages'])
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(2, priority_resource_uris_count)

        # Ensure that we don't add the same packages to the queue if they have
        # not yet been processed
        purls = [
            {'purl':'pkg:maven/ch.qos.reload4j/reload4j@1.2.24'},
            {'purl':'pkg:maven/com.esotericsoftware.kryo/kryo@2.24.0'},
            {'purl':'pkg:bitbucket/example/example@1.0.0'},
        ]
        data = {
            'packages': purls
        }
        response = self.client.post('/api/collect/index_packages/', data=data, content_type="application/json")
        self.assertEqual(0, response.data['queued_packages_count'])
        self.assertEqual([], response.data['queued_packages'])
        self.assertEqual(0, response.data['requeued_packages_count'])
        self.assertEqual([], response.data['requeued_packages'])
        self.assertEqual(2, response.data['unqueued_packages_count'])
        expected_unqueued_packages = [
            'pkg:maven/ch.qos.reload4j/reload4j@1.2.24',
            'pkg:maven/com.esotericsoftware.kryo/kryo@2.24.0',
        ]
        self.assertEqual(
            sorted(expected_unqueued_packages),
            sorted(response.data['unqueued_packages'])
        )
        self.assertEqual(1, response.data['unsupported_packages_count'])
        expected_unsupported_packages = [
            'pkg:bitbucket/example/example@1.0.0'
        ]
        self.assertEqual(expected_unsupported_packages, response.data['unsupported_packages'])

    @mock.patch("packagedb.api.get_all_versions")
    def test_package_api_index_packages_endpoint_with_vers(self, mock_get_all_versions):
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(0, priority_resource_uris_count)
        packages = [
            {
                "purl": "pkg:maven/ch.qos.reload4j/reload4j",
                "vers": "vers:maven/>=1.2.18.2|<=1.2.23",
            },
        ]
        data = {"packages": packages}

        mock_get_all_versions.return_value = [
            MavenVersion("1.2.18.0"),
            MavenVersion("1.2.18.1"),
            MavenVersion("1.2.18.2"),
            MavenVersion("1.2.18.3"),
            MavenVersion("1.2.18.4"),
            MavenVersion("1.2.18.5"),
            MavenVersion("1.2.19"),
            MavenVersion("1.2.20"),
            MavenVersion("1.2.21"),
            MavenVersion("1.2.22"),
            MavenVersion("1.2.23"),
            MavenVersion("1.2.24"),
            MavenVersion("1.2.25"),
        ]

        response = self.client.post(
            "/api/collect/index_packages/", data=data, content_type="application/json"
        )
        self.assertEqual(9, response.data["queued_packages_count"])

        expected_queued_packages = [
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.2",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.3",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.4",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.5",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.19",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.20",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.21",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.22",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.23",
        ]
        self.assertEqual(
            sorted(expected_queued_packages), sorted(response.data["queued_packages"])
        )
        self.assertEqual(0, response.data['requeued_packages_count'])
        self.assertEqual([], response.data['requeued_packages'])
        self.assertEqual(0, response.data["unqueued_packages_count"])
        self.assertEqual([], response.data["unqueued_packages"])
        self.assertEqual(0, response.data["unsupported_packages_count"])
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(9, priority_resource_uris_count)

    @mock.patch("packagedb.api.get_all_versions")
    def test_package_api_index_packages_endpoint_all_version_index(self, mock_get_all_versions):
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(0, priority_resource_uris_count)
        packages = [
            {
                "purl": "pkg:maven/ch.qos.reload4j/reload4j",
            },
        ]
        data = {"packages": packages}

        mock_get_all_versions.return_value = [
            MavenVersion("1.2.18.0"),
            MavenVersion("1.2.18.1"),
            MavenVersion("1.2.18.2"),
            MavenVersion("1.2.18.3"),
            MavenVersion("1.2.18.4"),
            MavenVersion("1.2.18.5"),
            MavenVersion("1.2.19"),
            MavenVersion("1.2.20"),
            MavenVersion("1.2.21"),
            MavenVersion("1.2.22"),
            MavenVersion("1.2.23"),
            MavenVersion("1.2.24"),
            MavenVersion("1.2.25"),
        ]

        response = self.client.post(
            "/api/collect/index_packages/", data=data, content_type="application/json"
        )
        self.assertEqual(13, response.data["queued_packages_count"])

        expected_queued_packages = [
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.0",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.1",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.2",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.3",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.4",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.18.5",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.19",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.20",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.21",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.22",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.23",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.24",
            "pkg:maven/ch.qos.reload4j/reload4j@1.2.25",
        ]
        self.assertEqual(
            sorted(expected_queued_packages), sorted(response.data["queued_packages"])
        )
        self.assertEqual(0, response.data['requeued_packages_count'])
        self.assertEqual([], response.data['requeued_packages'])
        self.assertEqual(0, response.data["unqueued_packages_count"])
        self.assertEqual([], response.data["unqueued_packages"])
        self.assertEqual(0, response.data["unsupported_packages_count"])
        self.assertEqual([], response.data["unsupported_packages"])
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(13, priority_resource_uris_count)
    
    def test_reindex_packages_bulk(self):
        self.assertEqual(False, self.scannableuri.rescan_uri)
        self.assertEqual(0, self.scannableuri.priority)
        self.assertEqual(self.scan_uuid, self.scannableuri.scan_uuid)
        self.assertEqual('error', self.scannableuri.scan_error)
        self.assertEqual('error', self.scannableuri.index_error)
        self.assertEqual(self.scan_request_date, self.scannableuri.scan_request_date)

        self.assertEqual(False, self.scannableuri2.rescan_uri)
        self.assertEqual(0, self.scannableuri2.priority)
        self.assertEqual(self.scan_uuid2, self.scannableuri2.scan_uuid)
        self.assertEqual('error', self.scannableuri2.scan_error)
        self.assertEqual('error', self.scannableuri2.index_error)
        self.assertEqual(self.scan_request_date2, self.scannableuri2.scan_request_date)

        packages = [
            # Existing package
            {
                "purl": 'pkg:maven/sample/Baz@90.12',
            },
            {
                "purl": 'pkg:npm/example/bar@56.78',
            },
            # NOt in DB and unsupported
            {
                "purl":'pkg:pypi/does/not-exist@1',
            },
        ]
        data = {"packages": packages, "reindex":True}

        existing_purls = [
            'pkg:maven/sample/Baz@90.12',
            'pkg:npm/example/bar@56.78',
        ]
        
        unsupported_purls = [
            'pkg:pypi/does/not-exist@1',
        ]

        response = self.client.post(f'/api/collect/index_packages/', data=data, content_type="application/json")

        self.assertEqual(2, response.data['requeued_packages_count'])
        self.assertListEqual(sorted(existing_purls), sorted(response.data['requeued_packages']))

        self.assertEqual(1, response.data['unsupported_packages_count'])
        self.assertListEqual(unsupported_purls, response.data['unsupported_packages'])

        self.assertEqual(0, response.data['queued_packages_count'])
        self.assertEqual([], response.data['queued_packages'])
        self.assertEqual(0, response.data["unqueued_packages_count"])
        self.assertEqual([], response.data["unqueued_packages"])


        self.scannableuri.refresh_from_db()
        self.assertEqual(True, self.scannableuri.rescan_uri)
        self.assertEqual(100, self.scannableuri.priority)
        self.assertEqual(None, self.scannableuri.scan_uuid)
        self.assertEqual(None, self.scannableuri.scan_error)
        self.assertEqual(None, self.scannableuri.index_error)
        self.assertEqual(None, self.scannableuri.scan_request_date)

        self.scannableuri2.refresh_from_db()
        self.assertEqual(True, self.scannableuri2.rescan_uri)
        self.assertEqual(100, self.scannableuri.priority)
        self.assertEqual(None, self.scannableuri2.scan_uuid)
        self.assertEqual(None, self.scannableuri2.scan_error)
        self.assertEqual(None, self.scannableuri2.index_error)
        self.assertEqual(None, self.scannableuri2.scan_request_date)
    

class ResourceApiTestCase(TestCase):

    def setUp(self):
        self.package_data = {
            'type': 'generic',
            'namespace': 'generic',
            'name': 'Foo',
            'version': '12.34',
            'qualifiers': 'test_qual=qual',
            'subpath': 'test_subpath',
            'download_url': 'http://example.com',
            'filename': 'Foo.zip',
            'sha1': 'testsha1',
            'md5': 'testmd5',
            'size': 101,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()

        self.resource1 = Resource.objects.create(
            path='foo',
            name='foo',
            sha1='sha1-1',
            md5='md5-1',
            package=self.package
        )
        self.resource1.refresh_from_db()
        self.resource2 = Resource.objects.create(
            path='foo/bar',
            name='bar',
            sha1='sha1-2',
            md5='md5-2',
            package=self.package
        )
        self.resource2.refresh_from_db()

    def test_api_resource_checksum_filter(self):
        filters = f'?md5={self.resource1.md5}&md5={self.resource2.md5}'
        response = self.client.get(f'/api/resources/{filters}')
        self.assertEqual(2, response.data['count'])
        names = sorted([result.get('name') for result in response.data['results']])
        expected_names = sorted([
            self.resource1.name,
            self.resource2.name,
        ])
        self.assertEquals(expected_names, names)

        filters = f'?sha1={self.resource1.sha1}&sha1={self.resource2.sha1}'
        response = self.client.get(f'/api/resources/{filters}')
        self.assertEqual(2, response.data["count"])
        names = sorted([result.get('name') for result in response.data['results']])
        expected_names = sorted([
            self.resource1.name,
            self.resource2.name,
        ])
        self.assertEquals(expected_names, names)

class PurlValidateApiTestCase(TestCase):

    def setUp(self):
        self.package_data = {
            'type': 'npm',
            'namespace': '',
            'name': 'foobar',
            'version': '1,1.0',
            'qualifiers': '',
            'subpath': '',
            'download_url': '',
            'filename': 'Foo.zip',
            'sha1': 'testsha1',
            'md5': 'testmd5',
            'size': 101,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()
    
    def test_api_purl_validation(self):
        data1 = {
            "purl": "pkg:npm/foobar@1.1.0",
            "check_existence": True,
        }
        response1 = self.client.get(f"/api/validate/", data=data1)

        data2 = {
            "purl": "pkg:npm/?foobar@1.1.0",
            "check_existence": True,
        }
        response2 = self.client.get(f"/api/validate/", data=data2)

        self.assertEquals(True, response1.data["valid"])
        self.assertEquals(True, response1.data["exists"])
        self.assertEquals(
            "The provided Package URL is valid, and the package exists in the upstream repo.",
            response1.data["message"],
        )

        self.assertEquals(False, response2.data["valid"])
        self.assertEquals(
            "The provided PackageURL is not valid.", response2.data["message"]
        )
    
    def test_api_purl_validation_unsupported_package_type(self):
        data1 = {
            "purl": "pkg:random/foobar@1.1.0",
            "check_existence": True,
        }
        response1 = self.client.get(f"/api/validate/", data=data1)


        self.assertEquals(True, response1.data["valid"])
        self.assertEquals(
            "The provided PackageURL is valid, but `check_existence` is not supported for this package type.", response1.data["message"]
        )
        self.assertEquals(None, response1.data["exists"])

    def test_api_purl_validation_empty_request(self):
        data1 = {}
        response1 = self.client.get(f"/api/validate/", data=data1)
        
        expected = {
            "errors": {
                "purl": [
                    "This field is required."
                ]
            }
        }

        self.assertAlmostEquals(expected, response1.data)
