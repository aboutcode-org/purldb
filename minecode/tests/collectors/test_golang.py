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

from django.test import TestCase as DjangoTestCase

from packageurl import PackageURL

import packagedb
from minecode.collectors import golang
from minecode.utils_test import JsonBasedTesting


class GoLangPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_extract_golang_subset_purl(self):
        test1 = "pkg:golang/github.com/rickar/cal/v2@2.1.23"
        test2 = "pkg:golang/github.com/rickar/cal/v2"
        expected_path1 = "rickar/cal"
        expected_version1 = "2.1.23"

        result_path1, result_version1 = golang.extract_golang_subset_purl(test1)
        result_path2, result_version2 = golang.extract_golang_subset_purl(test2)

        self.assertEqual(expected_path1, result_path1)
        self.assertEqual(result_version1, expected_version1)

        self.assertEqual(expected_path1, result_path2)
        self.assertEqual(result_version2, "")

    def test_gitlab_updated_purl(self):
        test1 = "pkg:golang/gitlab.com/gitlab-org/api/client-go@0.127.0"
        test2 = "pkg:golang/gitlab.com/gitlab-org/api/client-go"
        expected_path1 = "gitlab-org%2Fapi%2Fclient-go"
        expected_version1 = "0.127.0"

        result_path1, result_version1 = golang.gitlab_updated_purl(test1)
        result_path2, result_version2 = golang.gitlab_updated_purl(test2)

        self.assertEqual(expected_path1, result_path1)
        self.assertEqual(result_version1, expected_version1)

        self.assertEqual(expected_path1, result_path2)
        self.assertEqual(result_version2, "")

    def test_get_package_json_gitlab(self):
        json_contents = golang.get_package_json("xx_network%2Fprimitives", "gitlab")
        expected_id = 20321795
        expected_name = "primitives"

        self.assertEqual(json_contents.get("id"), expected_id)
        self.assertEqual(json_contents.get("name"), expected_name)

    def test_get_package_json_bitbucket(self):
        json_contents = golang.get_package_json("lebronto_kerovol/gwerror", "bitbucket")
        expected_full_name = "lebronto_kerovol/gwerror"
        expected_name = "gwerror"

        self.assertEqual(json_contents.get("full_name"), expected_full_name)
        self.assertEqual(json_contents.get("name"), expected_name)

    def test_map_go_package_gitlab(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string(
            "pkg:golang/gitlab.com/gitlab-org/api/client-go@0.127.0"
        )

        with open(self.get_test_loc("golang/client-go_0.127.0.json")) as file:
            package_json = json.load(file)
            golang.map_golang_package(package_url, package_json, ("test_pipeline"))
            package_count = packagedb.models.Package.objects.all().count()
            self.assertEqual(1, package_count)
            package = packagedb.models.Package.objects.all().first()
            expected_purl_str = "pkg:golang/gitlab.com/gitlab-org/api/client-go@0.127.0"
            expected_download_url = "https://gitlab.com/api/v4/projects/gitlab-org%2Fapi%2Fclient-go/repository/archive.zip?sha=v0.127.0"
            self.assertEqual(expected_purl_str, package.purl)
            self.assertEqual(expected_download_url, package.download_url)

    def test_map_go_package_bitbucket(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:golang/bitbucket.org/digi-sense/gg-core@0.3.64")

        with open(self.get_test_loc("golang/gg-core_0.3.64.json")) as file:
            package_json = json.load(file)
            golang.map_golang_package(package_url, package_json, ("test_pipeline"))
            package_count = packagedb.models.Package.objects.all().count()
            self.assertEqual(1, package_count)
            package = packagedb.models.Package.objects.all().first()
            expected_purl_str = "pkg:golang/bitbucket.org/digi-sense/gg-core@0.3.64"
            expected_download_url = "https://bitbucket.org/digi-sense/gg-core/get/v0.3.64.zip"
            self.assertEqual(expected_purl_str, package.purl)
            self.assertEqual(expected_download_url, package.download_url)

    def test_map_go_package_others(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:golang/golang.org/x/oauth2@0.29.0")

        with open(self.get_test_loc("golang/oauth2_0.29.0.json")) as file:
            package_json = json.load(file)
            golang.map_golang_package(package_url, package_json, ("test_pipeline"))
            package_count = packagedb.models.Package.objects.all().count()
            self.assertEqual(1, package_count)
            package = packagedb.models.Package.objects.all().first()
            expected_purl_str = "pkg:golang/golang.org/x/oauth2@0.29.0"
            expected_download_url = "https://proxy.golang.org/golang.org/x/oauth2/@v/v0.29.0.zip"
            self.assertEqual(expected_purl_str, package.purl)
            self.assertEqual(expected_download_url, package.download_url)

    def test_process_download_metadata(self):
        url = "https://bitbucket.org/digi-sense/gg-core/get/v0.3.64.zip"
        _package_json, filename = golang.process_download_metadata(url, {})
        exprected_filename = "digi-sense-gg-core-9d3dfdc43161.zip"
        self.assertEqual(exprected_filename, filename)
