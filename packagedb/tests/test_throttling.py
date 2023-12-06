#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from rest_framework.test import APIClient
from rest_framework.test import APITestCase


class ThrottleApiTests(APITestCase):
    def setUp(self):
        self.csrf_client_anon = APIClient(enforce_csrf_checks=True)
        self.csrf_client_anon_1 = APIClient(enforce_csrf_checks=True)

    def test_package_endpoint_throttling(self):
        # A anonymous user can only access /packages endpoint 10 times a day
        for i in range(0, 10):
            print(i)
            response = self.csrf_client_anon.get("/api/packages/")
            self.assertEqual(response.status_code, 200)

        response = self.csrf_client_anon.get("/api/packages/")
        # 429 - too many requests for anon user
        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.data.get("message"),
            "Your request has been throttled. Please contact support@nexb.com",
        )

        response = self.csrf_client_anon.get("/api/resources/")
        # 429 - too many requests for anon user
        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.data.get("message"),
            "Your request has been throttled. Please contact support@nexb.com",
        )
