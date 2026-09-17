#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from unittest import mock

from django.test import TestCase as DjangoTestCase

from minecode.collectors import gitlab
from minecode.utils_test import JsonBasedTesting


class GitlabPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    @mock.patch("minecode.collectors.gitlab.requests.get")
    def test_gitlab_get_all_package_version_author(self, mock_get):
        mock_json_data = [
            {
                "name": "v0.0.5",
                "commit": {
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                },
            },
            {
                "name": "v0.0.4",
                "commit": {
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                },
            },
            {
                "name": "v0.0.3",
                "commit": {
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                },
            },
            {
                "name": "v0.0.2",
                "commit": {
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                },
            },
            {
                "name": "v0.0.1",
                "commit": {
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                },
            },
            {
                "name": "v0.0.0",
                "commit": {
                    "author_name": "Sydney Anne Erickson",
                    "author_email": "sydney@elixxir.io",
                },
            },
        ]

        mock_response = mock.Mock()
        mock_response.json.return_value = mock_json_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        repo_path = "xx_network%2Fprimitives"
        version_author_list = gitlab.gitlab_get_all_package_version_author(repo_path)
        expected = [
            ("v0.0.5", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.4", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.3", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.2", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.1", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.0", "Sydney Anne Erickson", "sydney@elixxir.io"),
        ]

        self.assertEqual(expected, version_author_list)
