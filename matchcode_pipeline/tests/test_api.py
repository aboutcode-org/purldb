from pathlib import Path
from scanpipe.tests import dependency_data1
from scanpipe.tests import package_data1
from django.test import TransactionTestCase
from scanpipe.models import CodebaseRelation
from scanpipe.models import DiscoveredDependency
from scanpipe.models import Project
from scanpipe.models import CodebaseResource
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User


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

        self.matching_list_url = reverse("matching-list")
        self.project1_detail_url = reverse("matching-detail", args=[self.project1.uuid])

        self.user = User.objects.create_user("username", "e@mail.com", "secret")
        self.auth = f"Token {self.user.auth_token.key}"

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_scanpipe_api_project_list(self):
        response = self.csrf_client.get(self.matching_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, "input_root")
        self.assertNotContains(response, "extra_data")
        self.assertNotContains(response, "message_count")
        self.assertNotContains(response, "resource_count")
        self.assertNotContains(response, "package_count")
        self.assertNotContains(response, "dependency_count")
