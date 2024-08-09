#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.tests import dependency_data1
from scanpipe.tests import package_data1
from rest_framework import status


class MatchCodePipelineAPITest(TransactionTestCase):
    databases = {'default', 'packagedb'}
    data_location = Path(__file__).parent / 'data'

    def setUp(self):
        self.project1 = Project.objects.create(name='Analysis')
        self.resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path='daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO',
        )
        self.discovered_package1 = self.resource1.create_and_add_package(
            package_data1)
        self.discovered_dependency1 = DiscoveredDependency.create_from_data(
            self.project1, dependency_data1
        )
        self.codebase_relation1 = CodebaseRelation.objects.create(
            project=self.project1,
            from_resource=self.resource1,
            to_resource=self.resource1,
            map_type='java_to_class',
        )

        self.matching_list_url = reverse('matching-list')
        self.project1_detail_url = reverse(
            'matching-detail', args=[self.project1.uuid])

        self.user = User.objects.create_user(
            'username', 'e@mail.com', 'secret')
        self.auth = f'Token {self.user.auth_token.key}'

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_matchcode_pipeline_api_matching_list(self):
        response = self.csrf_client.get(self.matching_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data['count'])
        self.assertNotContains(response, 'input_root')
        self.assertNotContains(response, 'extra_data')
        self.assertNotContains(response, 'message_count')
        self.assertNotContains(response, 'resource_count')
        self.assertNotContains(response, 'package_count')
        self.assertNotContains(response, 'dependency_count')

    def test_matchcode_pipeline_api_matching_detail(self):
        response = self.csrf_client.get(self.project1_detail_url)
        self.assertIn(self.project1_detail_url, response.data['url'])
        self.assertEqual(str(self.project1.uuid), response.data['uuid'])
        self.assertEqual([], response.data['input_sources'])
        self.assertEqual([], response.data['runs'])
        self.assertEqual(1, response.data['resource_count'])
        self.assertEqual(1, response.data['package_count'])
        self.assertEqual(1, response.data['dependency_count'])
        self.assertEqual(1, response.data['relation_count'])

        expected = {'': 1}
        self.assertEqual(expected, response.data['codebase_resources_summary'])

        expected = {
            'total': 1,
            'with_missing_resources': 0,
            'with_modified_resources': 0,
        }
        self.assertEqual(
            expected, response.data['discovered_packages_summary'])

        expected = {
            'total': 1,
            'is_runtime': 1,
            'is_optional': 0,
            'is_resolved': 0,
        }
        self.assertEqual(
            expected, response.data['discovered_dependencies_summary'])

        expected = {'java_to_class': 1}
        self.assertEqual(expected, response.data['codebase_relations_summary'])

        input1 = self.project1.add_input_source(
            filename='file1', is_uploaded=True)
        input2 = self.project1.add_input_source(
            filename='file2', download_url='https://download.url')
        self.project1.save()
        response = self.csrf_client.get(self.project1_detail_url)
        expected = [
            {
                "filename": "file1",
                "download_url": "",
                "is_uploaded": True,
                "tag": "",
                "exists": False,
                "uuid": str(input1.uuid),
            },
            {
                "filename": "file2",
                "download_url": "https://download.url",
                "is_uploaded": False,
                "tag": "",
                "exists": False,
                "uuid": str(input2.uuid),
            },
        ]
        self.assertEqual(expected, response.data['input_sources'])

    @mock.patch('scanpipe.models.Run.execute_task_async')
    def test_matching_pipeline_api_matching_create(self, mock_execute_pipeline_task):
        # load upload_file contents
        test_out_loc = self.data_location / 'test-out.json'

        with open(test_out_loc) as f:
            data = {
                'upload_file': f,
            }
            # Send match request
            response = self.csrf_client.post(self.matching_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data['runs']))
        self.assertEqual('matching', response.data['runs'][0]['pipeline_name'])
        mock_execute_pipeline_task.assert_called_once()

        created_matching_project_detail_url = response.data['url']
        matching_project_uuid = response.data['uuid']
        results_url = reverse('matching-results', args=[matching_project_uuid])

        # Check that the file was uploaded
        response = self.csrf_client.get(created_matching_project_detail_url)
        self.assertEqual(
            'test-out.json', response.data['input_sources'][0]['filename'])

    @mock.patch('scanpipe.models.Run.execute_task_async')
    def test_matching_pipeline_api_matching_create_multiple_input_urls(self, mock_execute_pipeline_task):
        # load input_urls
        data = {
            'input_urls': 'https://registry.npmjs.org/asdf/-/asdf-1.2.2.tgz\r\nhttps://registry.npmjs.org/asdf/-/asdf-1.2.1.tgz',
        }

        # Send match request
        response = self.csrf_client.post(self.matching_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data['runs']))
        self.assertEqual('matching', response.data['runs'][0]['pipeline_name'])
        mock_execute_pipeline_task.assert_called_once()

        created_matching_project_detail_url = response.data['url']
        matching_project_uuid = response.data['uuid']
        results_url = reverse('matching-results', args=[matching_project_uuid])

        # Check that the file was uploaded
        response = self.csrf_client.get(created_matching_project_detail_url)
        input_sources = response.data['input_sources']
        self.assertEqual(2, len(input_sources))
        self.assertEqual('asdf-1.2.2.tgz', input_sources[0]['filename'])
        self.assertEqual('asdf-1.2.1.tgz', input_sources[1]['filename'])

    def test_matchcode_pipeline_api_run_detail(self):
        run1 = self.project1.add_pipeline('matching')
        url = reverse('run-detail', args=[run1.uuid])
        project1_detail_url = reverse('run-detail', args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(str(run1.uuid), response.data['uuid'])
        self.assertIn(project1_detail_url, response.data['project'])
        self.assertEqual('matching', response.data['pipeline_name'])
        self.assertEqual('', response.data['description'])
        self.assertEqual('', response.data['scancodeio_version'])
        self.assertIsNone(response.data['task_id'])
        self.assertIsNone(response.data['task_start_date'])
        self.assertIsNone(response.data['task_end_date'])
        self.assertEqual('', response.data['task_output'])
        self.assertIsNone(response.data['execution_time'])
        self.assertEqual(Run.Status.NOT_STARTED, response.data['status'])


class D2DPipelineAPITest(TransactionTestCase):
    databases = {'default', 'packagedb'}
    data_location = Path(__file__).parent / 'data'

    def setUp(self):
        self.project1 = Project.objects.create(name='Analysis')
        self.d2d_list_url = reverse('d2d-list')
        self.project1_detail_url = reverse(
            'd2d-detail', args=[self.project1.uuid])

        self.user = User.objects.create_user(
            'username', 'a@mail.com', 'secret')
        self.auth = f'Token {self.user.auth_token.key}'
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_d2d_pipeline_api_d2d_list(self):
        response = self.csrf_client.get(self.d2d_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data['count'])
        self.assertNotContains(response, 'input_root')
        self.assertNotContains(response, 'extra_data')
        self.assertNotContains(response, 'message_count')
        self.assertNotContains(response, 'resource_count')
        self.assertNotContains(response, 'package_count')
        self.assertNotContains(response, 'dependency_count')

    @mock.patch('scanpipe.models.Run.execute_task_async')
    def test_d2d_pipeline_api_d2d_create(self, mock_execute_pipeline_task):
        # load upload_file contents
        data = {
            'input_urls': ['https://github.com/nexB/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/from-data.zip#from',
                           'https://github.com/nexB/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/to-data.zip#to'],
        }

        # Send match request
        response = self.csrf_client.post(self.d2d_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data['runs']))
        mock_execute_pipeline_task.assert_called_once()
        response = self.csrf_client.get(response.data['url'])
        self.assertIn('codebase_resources_discrepancies', response.data)

    def test_d2d_pipeline_api_run_detail(self):
        run1 = self.project1.add_pipeline('d2d')
        url = reverse('run-detail', args=[run1.uuid])
        project1_detail_url = reverse('run-detail', args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(str(run1.uuid), response.data['uuid'])
        self.assertIn(project1_detail_url, response.data['project'])
        self.assertEqual('d2d', response.data['pipeline_name'])
        self.assertEqual(
            'Establish relationships between two code trees: deployment and development.', response.data['description'])
        self.assertEqual('', response.data['scancodeio_version'])
        self.assertIsNone(response.data['task_id'])
        self.assertIsNone(response.data['task_start_date'])
        self.assertIsNone(response.data['task_end_date'])
        self.assertEqual('', response.data['task_output'])
        self.assertIsNone(response.data['execution_time'])
        self.assertEqual(Run.Status.NOT_STARTED, response.data['status'])
