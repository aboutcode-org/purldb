#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json
import os
from unittest.mock import patch

from django.test import TestCase
from packageurl import PackageURL
import packagedb
from minecode.collectors import swift
from minecode.utils_test import JsonBasedTesting


class SwiftPriorityQueueTests(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_map_swift_package(self):
        package_url = PackageURL.from_string("pkg:swift/github.com/Alamofire/Alamofire@5.4.3")

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 0)

        swift.map_swift_package(package_url, ("test_pipelines"))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 2)
        package = packagedb.models.Package.objects.all().first()

        self.assertEqual(package.purl, str(package_url))

    @patch("minecode.collectors.swift.github.GithubSingleRepoVisitor")
    def test_map_swift_package1(self, mock_github_visitor):
        package_url = PackageURL.from_string(
            "pkg:swift/github.com/erikdrobne/SwiftUICoordinator@3.0.0"
        )

        expected_json_loc = self.get_test_loc("swift/swift-ui-coordinator.json")

        with open(expected_json_loc) as f:
            expected_json_contents = json.load(f)
            raw_repo_text = json.dumps(expected_json_contents)

        mock_github_visitor.return_value = (None, raw_repo_text, None)
        swift.map_swift_package(package_url, ("test_pipelines",))
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(package_count, 2)
        package = packagedb.models.Package.objects.all().first()
        self.assertEqual(package.purl, str(package_url))
