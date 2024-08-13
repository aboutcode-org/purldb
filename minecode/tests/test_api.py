#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core import signing
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from minecode.models import ScannableURI
from minecode.utils import get_webhook_url
from minecode.utils_test import JsonBasedTesting
from packagedb.models import Package
from packagedb.models import Resource


class ScannableURIAPITestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        self.scan_queue_worker_user = User.objects.create_user(
            username="username", email="e@mail.com", password="secret"
        )
        scan_queue_workers_group, _ = Group.objects.get_or_create(
            name="scan_queue_workers"
        )
        scan_queue_workers_group.user_set.add(self.scan_queue_worker_user)
        self.scan_queue_worker_auth = (
            f"Token {self.scan_queue_worker_user.auth_token.key}"
        )
        self.scan_queue_worker_client = APIClient(enforce_csrf_checks=True)
        self.scan_queue_worker_client.credentials(
            HTTP_AUTHORIZATION=self.scan_queue_worker_auth
        )
        self.scan_queue_worker_user_id_str = str(self.scan_queue_worker_user.id)

        # create a staff user
        self.staff_user = User.objects.create_user(
            username="staff_username",
            email="staff_e@mail.com",
            password="secret",
            is_staff=True,
        )
        self.staff_auth = f"Token {self.staff_user.auth_token.key}"
        self.staff_client = APIClient(enforce_csrf_checks=True)
        self.staff_client.credentials(HTTP_AUTHORIZATION=self.staff_auth)

        # create a regular user
        self.regular_user = User.objects.create_user(
            username="regular_username",
            email="regular_e@mail.com",
            password="secret",
        )
        self.regular_auth = f"Token {self.regular_user.auth_token.key}"
        self.regular_client = APIClient(enforce_csrf_checks=True)
        self.regular_client.credentials(HTTP_AUTHORIZATION=self.regular_auth)

        self.anonymous_client = APIClient()

        self.package1 = Package.objects.create(
            download_url="https://test-url.com/package1.tar.gz",
            type="type1",
            name="name1",
            version="1.0",
        )
        self.scannable_uri1 = ScannableURI.objects.create(
            uri="https://test-url.com/package1.tar.gz", package=self.package1
        )

        self.package2 = Package.objects.create(
            download_url="https://test-url.com/package2.tar.gz",
            type="type2",
            name="name2",
            version="2.0",
        )
        self.scannable_uri2 = ScannableURI.objects.create(
            uri="https://test-url.com/package2.tar.gz", package=self.package2
        )

        self.package3 = Package.objects.create(
            download_url="https://test-url.com/package3.tar.gz",
            type="type3",
            name="name3",
            version="3.0",
        )
        self.scannable_uri3 = ScannableURI.objects.create(
            uri="https://test-url.com/package3.tar.gz", package=self.package3
        )

    def test_api_scannable_uri_permissions(self):
        response = self.anonymous_client.get("/api/scan_queue/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.anonymous_client.get("/api/scan_queue/get_next_download_url/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.anonymous_client.post("/api/scan_queue/update_status/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.regular_client.get("/api/scan_queue/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.regular_client.get("/api/scan_queue/get_next_download_url/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.regular_client.post("/api/scan_queue/update_status/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_scannable_uri_list_endpoint(self):
        response = self.scan_queue_worker_client.get("/api/scan_queue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(3, response.data.get("count"))

        response = self.staff_client.get("/api/scan_queue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(3, response.data.get("count"))

    def test_api_scannable_uri_get_next_download_url(self):
        def check_webhook_url(self, webhook_url):
            webhook_url = response.data.get("webhook_url")
            key = webhook_url.rstrip("/").split("/")[-1]
            self.assertIn("/api/scan_queue/index_package_scan/", webhook_url)
            self.assertEqual(signing.loads(key), str(self.scan_queue_worker_user.id))

        response = self.scan_queue_worker_client.get(
            "/api/scan_queue/get_next_download_url/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("scannable_uri_uuid"), self.scannable_uri1.uuid
        )
        self.assertEqual(response.data.get("download_url"), self.scannable_uri1.uri)
        check_webhook_url(self, response.data.get("webhook_url"))

        response = self.scan_queue_worker_client.get(
            "/api/scan_queue/get_next_download_url/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("scannable_uri_uuid"), self.scannable_uri2.uuid
        )
        self.assertEqual(response.data.get("download_url"), self.scannable_uri2.uri)
        check_webhook_url(self, response.data.get("webhook_url"))

        response = self.scan_queue_worker_client.get(
            "/api/scan_queue/get_next_download_url/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("scannable_uri_uuid"), self.scannable_uri3.uuid
        )
        self.assertEqual(response.data.get("download_url"), self.scannable_uri3.uri)
        check_webhook_url(self, response.data.get("webhook_url"))

        response = self.scan_queue_worker_client.get(
            "/api/scan_queue/get_next_download_url/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("scannable_uri_uuid"), "")
        self.assertEqual(response.data.get("download_url"), "")
        self.assertEqual(response.data.get("webhook_url"), "")

        response = self.staff_client.get("/api/scan_queue/get_next_download_url/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("scannable_uri_uuid"), "")
        self.assertEqual(response.data.get("download_url"), "")
        self.assertEqual(response.data.get("webhook_url"), "")

    def test_api_scannable_uri_update_status(self):
        scannable_uri1_uuid = self.scannable_uri1.uuid
        scannable_uri2_uuid = self.scannable_uri2.uuid
        scannable_uri1_update_status_url = (
            f"/api/scan_queue/{scannable_uri1_uuid}/update_status/"
        )
        scannable_uri2_update_status_url = (
            f"/api/scan_queue/{scannable_uri2_uuid}/update_status/"
        )

        self.assertEqual(ScannableURI.SCAN_NEW, self.scannable_uri1.scan_status)
        data = {
            "scannable_uri_uuid": scannable_uri1_uuid,
            "scan_status": "failed",
            "scan_log": "scan_log",
        }
        response = self.scan_queue_worker_client.post(
            scannable_uri1_update_status_url, data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.scannable_uri1.refresh_from_db()
        self.assertEqual(ScannableURI.SCAN_FAILED, self.scannable_uri1.scan_status)
        self.assertEqual("scan_log", self.scannable_uri1.scan_error)

        data = {"scan_status": ""}
        response = self.scan_queue_worker_client.post(
            scannable_uri2_update_status_url, data=data
        )
        expected_response = {"error": "missing scan_status"}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expected_response, response.data)

        data = {"scan_status": "invalid"}
        response = self.scan_queue_worker_client.post(
            scannable_uri2_update_status_url, data=data
        )
        expected_response = {"error": "invalid scan_status: invalid"}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expected_response, response.data)

        data = {}
        response = self.scan_queue_worker_client.post(
            "/api/scan_queue/asdf/", data=data
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_api_scannable_uri_update_status_update_finished_scannable_uri(self):
        scannable_uri_uuid = self.scannable_uri3.uuid
        for scan_status in [
            ScannableURI.SCAN_INDEXED,
            ScannableURI.SCAN_FAILED,
            ScannableURI.SCAN_TIMEOUT,
            ScannableURI.SCAN_INDEX_FAILED,
        ]:
            self.scannable_uri3.scan_status = scan_status
            self.scannable_uri3.save()
            data = {"scannable_uri_uuid": scannable_uri_uuid, "scan_status": "scanned"}
            response = self.scan_queue_worker_client.post(
                f"/api/scan_queue/{scannable_uri_uuid}/update_status/", data=data
            )
            expected_response = {
                "error": "cannot update status for scannable_uri "
                f"{self.scannable_uri3.uuid}: scannable_uri has finished "
                f'with status "{ScannableURI.SCAN_STATUSES_BY_CODE[scan_status]}"'
            }
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(expected_response, response.data)

    def test_api_scannable_uri_index_package_scan(self):
        self.assertFalse(self.package2.md5)
        self.assertFalse(self.package2.sha1)
        self.assertFalse(self.package2.sha256)
        self.assertFalse(self.package2.sha512)
        self.assertFalse(self.package2.size)
        self.assertFalse(self.package2.declared_license_expression)
        self.assertFalse(self.package2.copyright)
        self.assertEqual(0, Resource.objects.all().count())
        scan_file_location = self.get_test_loc("scancodeio/get_scan_data.json")
        summary_file_location = self.get_test_loc(
            "scancodeio/scan_summary_response.json"
        )
        project_extra_data = {
            "scannable_uri_uuid": self.scannable_uri2.uuid,
            "md5": "md5",
            "sha1": "sha1",
            "sha256": "sha256",
            "sha512": "sha512",
            "size": 100,
        }
        with (
            open(scan_file_location) as scan_file,
            open(summary_file_location) as summary_file,
        ):
            results = json.load(scan_file)
            summary = json.load(summary_file)
            data = {
                "project": {
                    "extra_data": project_extra_data,
                },
                "results": results,
                "summary": summary,
            }

        webhook_url = get_webhook_url(
            "index_package_scan", self.scan_queue_worker_user.id
        )

        response = self.scan_queue_worker_client.post(
            webhook_url, data=data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.scannable_uri2.refresh_from_db()
        self.assertEqual(ScannableURI.SCAN_INDEXED, self.scannable_uri2.scan_status)
        self.package2.refresh_from_db()
        self.assertEqual("md5", self.package2.md5)
        self.assertEqual("sha1", self.package2.sha1)
        self.assertEqual("sha256", self.package2.sha256)
        self.assertEqual("sha512", self.package2.sha512)
        self.assertEqual(100, self.package2.size)
        self.assertEqual("apache-2.0", self.package2.declared_license_expression)
        self.assertEqual(
            "Copyright (c) Apache Software Foundation", self.package2.copyright
        )
        self.assertFalse(self.scannable_uri2.scan_error)
        self.assertEqual(64, Resource.objects.all().count())
