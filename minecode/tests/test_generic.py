#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.test import TestCase as DjangoTestCase
from packagedcode.maven import _parse
from packageurl import PackageURL

from minecode.route import NoRouteAvailable
from minecode.utils_test import JsonBasedTesting
from minecode.visitors import generic
from packagedb.models import Package


class GenericPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    def test_process_request(self):
        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl = "pkg:generic/test@1.0.0?download_url=http://example.com/test.tar.gz"
        error_msg = generic.process_request(purl)

        self.assertEqual(None, error_msg)
        package_count = Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = Package.objects.first()
        self.assertEqual("test", package.name)
        self.assertEqual("1.0.0", package.version)
        self.assertEqual("http://example.com/test.tar.gz", package.download_url)

    def test_process_request_no_download_url(self):
        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl = "pkg:generic/test@1.0.0"

        with self.assertRaises(NoRouteAvailable):
            generic.process_request(purl)

    def test_map_generic_package(self):
        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl = "pkg:generic/test@1.0.0?download_url=http://example.com/test.tar.gz"
        package_url = PackageURL.from_string(purl)
        error_msg = generic.map_generic_package(package_url)

        self.assertEqual("", error_msg)
        package_count = Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = Package.objects.first()
        self.assertEqual("test", package.name)
        self.assertEqual("1.0.0", package.version)
        self.assertEqual("http://example.com/test.tar.gz", package.download_url)

    def test_process_request_dir_listed(self):
        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl = "pkg:generic/ipkg@0.99.33"
        error_msg = generic.process_request_dir_listed(purl)

        self.assertEqual(None, error_msg)
        package_count = Package.objects.all().count()
        self.assertEqual(1, package_count)

        package = Package.objects.first()
        self.assertEqual("ipkg", package.name)
        self.assertEqual("0.99.33", package.version)
        self.assertEqual(
            "https://web.archive.org/web/20090326020239/http:/handhelds.org/download/packages/ipkg/ipkg_0.99.33_arm.ipk",
            package.download_url,
        )
