#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.contrib.postgres.search import SearchVector
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from packagedb.models import Package
from packagedb.models import Resource


class ResourceAPITestCase(TestCase):

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
        self.assertTrue(response.data.get('is_file'))

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
        self.assertTrue(test_resource.get('is_file'))

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
        self.assertTrue(test_resource.get('is_file'))

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
        self.assertTrue(test_resource.get('is_file'))

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
        self.assertTrue(test_resource.get('is_file'))


class PackageApiTestCase(TestCase):

    def setUp(self):
        self.package_data = {
            'type': 'generic',
            'namespace': 'generic',
            'name': 'Foo',
            'version': '12.34',
            'qualifiers': 'testqual',
            'subpath': 'testsub',
            'download_url': 'http://example.com',
            'filename': 'Foo.zip',
            'sha1': 'testsha1',
            'md5': 'testmd5',
            'size': 100,
            'extra_data': json.dumps({'test2': 'data2'})
        }

        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()

        self.package.append_to_history('test-message')
        self.package.save()

        self.test_url = 'http://testserver/api/packages/{}/'

        self.client = APIClient()

    def test_package_api_list_endpoint(self):
        response = self.client.get('/api/packages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

    def test_package_api_list_endpoint_filter(self):
        for key, value in self.package_data.items():
            response = self.client.get('/api/packages/?{}={}'.format(key, value))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

    def test_package_api_list_endpoint_filter_by_purl_fields_ignores_case(self):
        for key, value in self.package_data.items():
            # Skip non-purl fields
            if key not in ['type', 'namespace', 'name', 'version', 'qualifiers', 'subpath',
                           'download_url', 'filename']:
                continue

            response = self.client.get('/api/packages/?{}__iexact={}'.format(key, value.lower()))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

            response = self.client.get('/api/packages/?{}__iexact={}'.format(key, value.upper()))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(1, response.data.get('count'))

    def test_package_api_list_endpoint_search(self):
        # Populate the search vector field. This is done via Django signals
        # outside of the tests.
        Package.objects.filter(uuid=self.package.uuid).update(
            search_vector=SearchVector('namespace', 'name', 'version', 'download_url')
        )

        # Create a dummy package to verify search filter works.
        Package.objects.create(
            namespace='dummy-namespace',
            name='dummy-name',
            version='12.35',
            download_url='https://dummy.com/dummy'
        )

        for key, value in self.package_data.items():
            # Skip since we only search on one field
            if key not in ['namespace', 'name', 'version', 'download_url']:
                continue

            response = self.client.get('/api/packages/?search={}'.format(value))
            assert response.status_code == status.HTTP_200_OK
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
                self.assertEqual(value.lower(), getattr(self.package, key))
                continue

            if key == 'history':
                self.assertIn('test-message', value)

            self.assertTrue(hasattr(self.package, key))
            if key in self.package_data.keys():
                self.assertEqual(value, getattr(self.package, key))

    def test_api_package_latest_version_action(self):
        p1 = Package.objects.create(download_url='http://a.a', name='name', version='1.0')
        p2 = Package.objects.create(download_url='http://b.b', name='name', version='2.0')
        p3 = Package.objects.create(download_url='http://c.c', name='name', version='3.0')

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
        self.assertEqual(10, len(response.data))

        for result, i in zip(response.data, range(0, 10)):
            self.assertEqual(result.get('path'), 'path{}/'.format(i))


class PackageApiPurlFilterTestCase(TestCase):

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

        self.package1 = Package.objects.create(**self.package_data1)
        self.package2 = Package.objects.create(**self.package_data2)

        self.purl1 = self.package1.package_url
        self.purl2 = self.package2.package_url

        self.missing_purl = 'pkg:PYPI/Django_package@1.11.1.dev1'

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
        self.assertEqual(2, response.data.get('count'))

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
        self.assertEqual(2, response.data.get('count'))
