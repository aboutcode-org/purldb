#
# Copyright (c) nexB Inc. and others. All rights reserved.
# PurlDB is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.test import TestCase


class TestViews(TestCase):
    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        assert response.status_code == 200
        assert response["content-type"] == "text/plain"
        assert response.content == b"User-agent: *\nDisallow: *\n"

        response = self.client.post("/robots.txt")
        assert response.status_code == 405
