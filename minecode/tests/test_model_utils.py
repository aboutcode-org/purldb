#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TransactionTestCase

from packagedcode.maven import _parse

from minecode.model_utils import merge_or_create_package
from minecode.model_utils import update_or_create_resource
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import MiningTestCase
from packagedb.models import Package
from packagedb.models import Resource


class ModelUtilsTestCase(MiningTestCase, JsonBasedTesting):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        pom_loc = self.get_test_loc("maven/pom/pulsar-2.5.1.pom")
        self.scanned_package = _parse("maven_pom", "maven", "Java", location=pom_loc)
        self.scanned_package.download_url = "https://repo1.maven.org/maven2/org/apache/pulsar/pulsar/2.5.1/pulsar-2.5.1.jar"

    def test_merge_or_create_package_create_package(self):
        self.assertEqual(0, Package.objects.all().count())
        package, created, merged, map_error = merge_or_create_package(
            self.scanned_package, visit_level=50
        )
        self.assertEqual(1, Package.objects.all().count())
        self.assertEqual(package, Package.objects.all().first())
        self.assertTrue(created)
        self.assertFalse(merged)
        self.assertEqual("", map_error)
        self.assertTrue(package.created_date)
        self.assertTrue(package.last_modified_date)
        expected_loc = self.get_test_loc("model_utils/created_package.json")
        self.check_expected_results(
            package.to_dict(),
            expected_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )

    def test_merge_or_create_package_merge_package(self):
        # ensure fields get updated
        # ensure history is properly updated
        package = Package.objects.create(
            type="maven",
            namespace="org.apache.pulsar",
            name="pulsar",
            version="2.5.1",
            download_url="https://repo1.maven.org/maven2/org/apache/pulsar/pulsar/2.5.1/pulsar-2.5.1.jar",
        )
        before_merge_loc = self.get_test_loc("model_utils/before_merge.json")
        self.check_expected_results(
            package.to_dict(),
            before_merge_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )
        package, created, merged, map_error = merge_or_create_package(
            self.scanned_package, visit_level=50
        )
        self.assertEqual(1, Package.objects.all().count())
        self.assertEqual(package, Package.objects.all().first())
        self.assertFalse(created)
        self.assertTrue(merged)
        self.assertEqual("", map_error)
        expected_loc = self.get_test_loc("model_utils/after_merge.json")
        self.check_expected_results(
            package.to_dict(),
            expected_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )
        history = package.get_history()
        self.assertEqual(1, len(history))
        entry = history[0]
        timestamp = entry["timestamp"]
        message = entry["message"]
        self.assertEqual(
            "Package field values have been updated.",
            message,
        )
        last_modified_date_formatted = package.last_modified_date.strftime(
            "%Y-%m-%d-%H:%M:%S"
        )
        self.assertEqual(timestamp, last_modified_date_formatted)
        data = entry["data"]
        updated_fields = data["updated_fields"]
        expected_updated_fields_loc = self.get_test_loc(
            "model_utils/expected_updated_fields.json"
        )
        self.check_expected_results(
            updated_fields, expected_updated_fields_loc, regen=FIXTURES_REGEN
        )


class UpdateORCreateResourceTest(TransactionTestCase):
    def setUp(self):
        self.package = Package.objects.create(download_url="test-pkg.com")
        self.resource_path = "root/test.c"
        self.old_extra_data = {
            "source_symbols": [
                "Old-symb1",
                "Old-symb2",
            ]
        }

        self.new_extra_data = {
            "source_symbols": [
                "New-symb1",
                "New-symb2",
            ]
        }

        self.resource = Resource.objects.create(
            package=self.package,
            path=self.resource_path,
            extra_data=self.old_extra_data,
        )

    def test_update_or_create_resource_update(self):
        self.assertEqual(self.old_extra_data, self.resource.extra_data)

        update_or_create_resource(
            self.package,
            {"extra_data": self.new_extra_data, "path": self.resource_path},
        )
        self.resource.refresh_from_db()

        self.assertEqual(self.new_extra_data, self.resource.extra_data)

    def test_update_or_create_resource_create(self):
        update_or_create_resource(
            self.package,
            {
                "type": "file",
                "name": "test_new",
                "extension": ".c",
                "is_binary": False,
                "is_text": False,
                "is_archive": False,
                "is_media": False,
                "is_key_file": False,
                "extra_data": self.new_extra_data,
                "path": "root/test_new.c",
            },
        )

        resource = Resource.objects.get(path="root/test_new.c")
        self.assertEqual(self.new_extra_data, resource.extra_data)
