#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TestCase as DjangoTestCase

from minecode.collectors import gitlab
from minecode.utils_test import JsonBasedTesting

from unittest import mock


class GitlabPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    @mock.patch("requests.get")
    def test_gitlab_get_all_package_version_author(self, mock_request_get):
        repo_path = "xx_network%2Fprimitives"

        mock_data = [
            {
                "name": "v0.0.4",
                "message": "",
                "target": "f7c71b05e13e619feabdc078678d9eb8ff2def3c",
                "commit": {
                    "id": "f7c71b05e13e619feabdc078678d9eb8ff2def3c",
                    "short_id": "f7c71b05",
                    "created_at": "2023-12-06T01:50:27.000+00:00",
                    "parent_ids": ["62d7bebec4063ba4a6da607a78b32bd24b357283"],
                    "title": "Update copyright",
                    "message": "Update copyright\n",
                    "author_name": "Richard T. Carback III",
                    "author_email": "rick.carback@gmail.com",
                    "authored_date": "2023-12-06T01:50:27.000+00:00",
                    "committer_name": "Richard T. Carback III",
                    "committer_email": "rick.carback@gmail.com",
                    "committed_date": "2023-12-06T01:50:27.000+00:00",
                    "trailers": {},
                    "extended_trailers": {},
                    "web_url": "https://gitlab.com/xx_network/primitives/-/commit/f7c71b05e13e619feabdc078678d9eb8ff2def3c",
                },
                "release": None,
                "protected": False,
                "created_at": None,
            },
            {
                "name": "v0.0.0",
                "message": "",
                "target": "a0cd942ed608d4950217aa4099358ab168435e1d",
                "commit": {
                    "id": "a0cd942ed608d4950217aa4099358ab168435e1d",
                    "short_id": "a0cd942e",
                    "created_at": "2020-08-05T16:51:29.000+00:00",
                    "parent_ids": [
                        "2aac33c9bb95b47c36f995522801c40c2f4e51a4",
                        "f99f7a7284da1cd621324ee0a1714a461e055adf",
                    ],
                    "title": "Merge branch 'release' into 'master'",
                    "message": "Merge branch 'release' into 'master'\n\nUse xxn primitives ID and NDF packages\n\nSee merge request xx_network/primitives!1",
                    "author_name": "Sydney Anne Erickson",
                    "author_email": "sydney@elixxir.io",
                    "authored_date": "2020-08-05T16:51:29.000+00:00",
                    "committer_name": "Sydney Anne Erickson",
                    "committer_email": "sydney@elixxir.io",
                    "committed_date": "2020-08-05T16:51:29.000+00:00",
                    "trailers": {},
                    "extended_trailers": {},
                    "web_url": "https://gitlab.com/xx_network/primitives/-/commit/a0cd942ed608d4950217aa4099358ab168435e1d",
                },
                "release": None,
                "protected": False,
                "created_at": None,
            },
        ]
        mock_response = mock.Mock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_request_get.return_value = mock_response

        version_author_list = gitlab.gitlab_get_all_package_version_author(repo_path)
        expected = [
            ("v0.0.4", "Richard T. Carback III", "rick.carback@gmail.com"),
            ("v0.0.0", "Sydney Anne Erickson", "sydney@elixxir.io"),
        ]
        for item in version_author_list:
            self.assertIn(item, expected)
