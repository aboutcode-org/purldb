from pathlib import Path
from unittest import mock
import json
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from packagedb.models import ApiUser
from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import Project
from scanpipe.tests import dependency_data1
from scanpipe.tests import package_data1
from rest_framework import status
from packagedb.models import Package


class MatchCodePipelineAPITest(TransactionTestCase):
    databases = {'default', 'packagedb'}
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        self.discovered_package1 = self.resource1.create_and_add_package(package_data1)
        self.discovered_dependency1 = DiscoveredDependency.create_from_data(
            self.project1, dependency_data1
        )
        self.codebase_relation1 = CodebaseRelation.objects.create(
            project=self.project1,
            from_resource=self.resource1,
            to_resource=self.resource1,
            map_type="java_to_class",
        )

        self.package1 = Package.objects.create(
            type=package_data1['type'],
            namespace=package_data1['namespace'],
            name=package_data1['name'],
            version=package_data1['version'],
            sha1='deadbeef',
        )

        self.matching_list_url = reverse("matching-list")
        self.project1_detail_url = reverse("matching-detail", args=[self.project1.uuid])

        self.user = User.objects.create_user("username", "e@mail.com", "secret")
        self.auth = f"Token {self.user.auth_token.key}"

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_matchcode_pipeline_api_matching_list(self):
        response = self.csrf_client.get(self.matching_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, "input_root")
        self.assertNotContains(response, "extra_data")
        self.assertNotContains(response, "message_count")
        self.assertNotContains(response, "resource_count")
        self.assertNotContains(response, "package_count")
        self.assertNotContains(response, "dependency_count")

    def test_matchcode_pipeline_api_matching_detail(self):
        response = self.csrf_client.get(self.project1_detail_url)
        self.assertIn(self.project1_detail_url, response.data["url"])
        self.assertEqual(str(self.project1.uuid), response.data["uuid"])
        self.assertEqual([], response.data["input_sources"])
        self.assertEqual([], response.data["runs"])
        self.assertEqual(1, response.data["resource_count"])
        self.assertEqual(1, response.data["package_count"])
        self.assertEqual(1, response.data["dependency_count"])
        self.assertEqual(1, response.data["relation_count"])

        expected = {"": 1}
        self.assertEqual(expected, response.data["codebase_resources_summary"])

        expected = {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0,
        }
        self.assertEqual(expected, response.data["discovered_packages_summary"])

        expected = {
            "total": 1,
            "is_runtime": 1,
            "is_optional": 0,
            "is_resolved": 0,
        }
        self.assertEqual(expected, response.data["discovered_dependencies_summary"])

        expected = {"java_to_class": 1}
        self.assertEqual(expected, response.data["codebase_relations_summary"])

        self.project1.add_input_source(filename="file1", source="uploaded")
        self.project1.add_input_source(filename="file2", source="https://download.url")
        self.project1.save()
        response = self.csrf_client.get(self.project1_detail_url)
        expected = [
            {"filename": "file1", "source": "uploaded"},
            {"filename": "file2", "source": "https://download.url"},
        ]
        self.assertEqual(expected, response.data["input_sources"])

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_api_project_create(self, mock_execute_pipeline_task):
        # load upload_file contents
        test_out_loc = self.data_location / "test-out.json"
        content = open(test_out_loc, 'r')
        data = {
            "upload_file": content,
        }

        # Send match request
        response = self.csrf_client.post(self.matching_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual('matching', response.data["runs"][0]["pipeline_name"])
        mock_execute_pipeline_task.assert_called_once()

        created_matching_project_detail_url = response.data["url"]
        matching_project_uuid = response.data['uuid']
        results_url = reverse("matching-results", args=[matching_project_uuid])

        # Check that the file was uploaded
        response = self.csrf_client.get(created_matching_project_detail_url)
        self.assertEqual('test-out.json', response.data['input_sources'][0]['filename'])

        # Get and check results
        response = self.csrf_client.get(results_url)
        results = [line.decode('utf-8') for line in list(response.streaming_content)]
        results = ''.join(results)
        print(results)
        results = json.loads(results)

        expected_results_loc = self.data_location / "match-creation-api-results.json"
        with open(expected_results_loc, 'r') as f:
            expected_results = json.load(f)

        self.assertEqual(expected_results, results)
