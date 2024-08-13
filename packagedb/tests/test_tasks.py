#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from unittest.mock import patch

from django.test import TestCase

from fetchcode.package_versions import PackageVersion

from minecode.models import PriorityResourceURI
from packagedb.models import Package
from packagedb.models import PackageWatch
from packagedb.tasks import is_supported_watch_ecosystem
from packagedb.tasks import watch_new_packages


class PackageWatchTasksTestCase(TestCase):
    @patch("packagedb.models.PackageWatch.create_new_job")
    def setUp(self, mock_create_new_job):
        mock_create_new_job.return_value = None

        self.package_watch1 = PackageWatch.objects.create(
            package_url="pkg:maven/org.test/test-package"
        )

        self.package_watch2 = PackageWatch.objects.create(
            package_url="pkg:maven/org.test/test-package2"
        )

        self.package_watch3 = PackageWatch.objects.create(
            package_url="pkg:unknown/org.test/test-package3"
        )

        package_download_url = "http://anotherexample.com"
        self.package_data1 = {
            "type": "maven",
            "namespace": "org.test",
            "name": "test-package2",
            "version": "v1.0.1",
            "qualifiers": "",
            "subpath": "",
            "download_url": package_download_url,
            "filename": "test-package2.zip",
            "sha1": "testsha1-1",
            "md5": "testmd5-1",
            "size": 100,
        }
        self.package1 = Package.objects.create(**self.package_data1)

    @patch("packagedb.tasks.is_supported_watch_ecosystem")
    @patch("fetchcode.package_versions.versions")
    def test_watch_new_packages_without_local_package(
        self, mock_versions, mock_is_supported_watch_ecosystem
    ):
        mock_is_supported_watch_ecosystem.return_value = True
        mock_versions.return_value = [
            PackageVersion(value="v1.0.1"),
            PackageVersion(value="v1.2.1"),
            PackageVersion(value="v3.0.1"),
        ]

        watch_new_packages(self.package_watch1.package_url)
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(3, priority_resource_uris_count)

    @patch("packagedb.tasks.is_supported_watch_ecosystem")
    @patch("fetchcode.package_versions.versions")
    def test_watch_new_packages_with_local_package(
        self, mock_versions, mock_is_supported_watch_ecosystem
    ):
        mock_is_supported_watch_ecosystem.return_value = True
        mock_versions.return_value = [
            PackageVersion(value="v1.0.1"),
            PackageVersion(value="v1.2.1"),
            PackageVersion(value="v3.0.1"),
        ]

        watch_new_packages(self.package_watch2.package_url)
        priority_resource_uris_count = PriorityResourceURI.objects.all().count()
        self.assertEqual(2, priority_resource_uris_count)

    def test_is_supported_watch_ecosystem(self):
        result1 = is_supported_watch_ecosystem(self.package_watch1)

        result2 = is_supported_watch_ecosystem(self.package_watch3)

        self.assertEqual(True, result1)
        self.assertEqual(None, self.package_watch1.watch_error)

        self.assertEqual(False, result2)
        self.assertEqual(
            "`unknown` ecosystem is not supported by fetchcode",
            self.package_watch3.watch_error,
        )
