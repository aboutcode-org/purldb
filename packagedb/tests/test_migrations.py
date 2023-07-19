#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from uuid import uuid4

from django.apps import apps

from minecode.utils_test import TestMigrations


class TestPackageSetCreation(TestMigrations):
    app_name = "packagedb"
    migrate_from = "0069_packageset_package_package_sets"
    migrate_to = "0070_auto_20230706_0045"

    def setUpBeforeMigration(self, apps):
        # using get_model to avoid circular import
        Package = apps.get_model("packagedb", "Package")
        self.package_set1 = uuid4()
        self.package_set2 = uuid4()
        # A package set containing package1 and package2 should be created
        self.package1 = Package.objects.create(
            download_url="http://example.com/example.tar.gz",
            type="maven",
            namespace="example",
            name="example",
            version="1.0.0",
            package_set=self.package_set1,
        )
        self.package2 = Package.objects.create(
            download_url="http://example.com/example-sources.tar.gz",
            type="maven",
            namespace="example",
            name="example",
            version="1.0.0",
            qualifiers="classifier=sources",
            package_set=self.package_set1,
        )
        # The package set for package3 should not be created, since there's only one package in the set
        self.package3 = Package.objects.create(
            download_url="http://example.com/something-else.tar.gz",
            type="maven",
            namespace="example",
            name="something-else",
            version="2.0.0",
            package_set=self.package_set2,
        )
        # A package set should be created that contains package4 and package5
        self.package4 = Package.objects.create(
            download_url="http://example.com/bar.tar.gz",
            type="maven",
            namespace="",
            name="bar",
            version="0.0.1",
        )
        self.package5 = Package.objects.create(
            download_url="http://example.com/bar-sources.tar.gz",
            type="maven",
            namespace="",
            name="bar",
            version="0.0.1",
            qualifiers="classifier=sources",
        )
        # We should not have a package set created for package6
        self.package6 = Package.objects.create(
            download_url="http://example.com/foo.tar.gz",
            type="npm",
            namespace="",
            name="foo",
            version="0.0.1",
        )
        self.packages = [
            self.package1,
            self.package2,
            self.package3,
            self.package4,
            self.package5,
            self.package6,
        ]

        for package in self.packages:
            package.save()

    def test_package_set_creation(self):
        # using get_model to avoid circular import
        PackageSet = apps.get_model("packagedb", "PackageSet")
        packages_in_package_sets = [
            self.package1,
            self.package2,
            self.package4,
            self.package5,
        ]
        self.assertTrue(all(package.package_sets for package in packages_in_package_sets))

        package_set1 = PackageSet.objects.get(uuid=self.package_set1)
        self.assertTrue(package_set1)
        self.assertRaises(PackageSet.DoesNotExist, PackageSet.objects.get, uuid=self.package_set2)
        self.assertEqual(1, self.package1.package_sets.count())
        self.assertEqual(1, self.package2.package_sets.count())
        self.assertEqual(package_set1.uuid, self.package1.package_sets.first().uuid)
        self.assertEqual(package_set1.uuid, self.package2.package_sets.first().uuid)

        self.assertEqual(0,  self.package3.package_sets.count())

        self.assertEqual(1,  self.package4.package_sets.count())
        self.assertEqual(1,  self.package5.package_sets.count())
        self.assertEqual(self.package4.package_sets.first(), self.package5.package_sets.first())
        package_set_for_package4_and_package5 = self.package4.package_sets.first()
        self.assertEqual(2, package_set_for_package4_and_package5.packages.count())

        self.assertEqual(0, self.package6.package_sets.count())
