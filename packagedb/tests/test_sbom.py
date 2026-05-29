#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TestCase


from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from packagedb.models import Package
from packagedb.models import DependentPackage
from packagedb import sbom


class PackageDBSBOMTestCase(JsonBasedTesting, TestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        self.package_data = {
            "type": "generic",
            "namespace": "generic",
            "name": "Foo",
            "version": "12.34",
            "qualifiers": "test_qual=qual",
            "subpath": "test_subpath",
            "download_url": "http://example.com",
            "filename": "Foo.zip",
            "sha1": "testsha1",
            "md5": "testmd5",
            "size": 101,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()
        self.package_dependency = DependentPackage.objects.create(
            package=self.package,
            purl="pkg:generic/dep1",
        )
        self.package_dependency2 = DependentPackage.objects.create(
            package=self.package,
            purl="pkg:generic/dep2",
        )

    def test_package_api_sbom_endpoint(self):
        expected = self.get_test_loc("sbom/package-sbom-expected.json")
        result = sbom.to_cyclonedx(self.package)
        self.check_expected_results(
            result,
            expected,
            fields_to_remove=["serialNumber", "bom-ref", "timestamp", "ref", "properties"],
            regen=FIXTURES_REGEN,
        )
