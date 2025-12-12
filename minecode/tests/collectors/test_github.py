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

from minecode.collectors import github
from minecode.utils_test import JsonBasedTesting


class GithubPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_github_get_all_versions(self):
        repo_path = "aboutcode-org/purldb"
        versions = github.github_get_all_versions(repo_path)
        expected = [
            "v7.0.0",
            "v6.0.0",
            "v5.0.1",
            "v5.0.0",
            "v3.0.0",
            "v2.0.0",
            "purldb-toolkit-v0.1.0",
            "purl2vcs-v2.0.0",
            "purl2vcs-v1.0.2",
            "pre-scan-queue-update",
            "matchcode-toolkit-v3.0.0",
            "matchcode-toolkit-v1.1.1",
            "minecode-pipelines/v0.0.1b3",
            "minecode-pipelines/v0.0.1b4",
            "minecode-pipelines/v0.0.1b5",
            "minecode-pipelines/v0.0.1b6",
            "minecode-pipelines/v0.0.1b7",
            "minecode-pipelines/v0.0.1b8",
        ]
        for item in expected:
            self.assertIn(item, versions)
