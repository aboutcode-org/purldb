#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ApproximateResourceContentIndex
from matchcode.models import ExactFileIndex
from minecode import indexing
from minecode.models import ScannableURI
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import MiningTestCase
from packagedb.models import Package
from packagedb.models import Resource


class IndexingTest(MiningTestCase, JsonBasedTesting):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        self.package1 = Package.objects.create(
            download_url='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            type='maven',
            namespace='',
            name='wagon-api',
            version='20040705.181715'
        )

        self.package2 = Package.objects.create(
            download_url='https://github.com/aboutcode-org/elf-inspector/raw/4333e1601229da87fa88961389d7397af6e027c4/tests/data/dwarf_and_elf/analyze.so.debug',
            type='generic',
            namespace='',
            name='debug',
            version='1.23'
        )

    def test_indexing_index_package_files(self):
        # Ensure ApproximateDirectoryStructureIndex, ExactPackageArchiveIndex,
        # and ExactFileIndex tables are empty
        self.assertEqual(0, ApproximateDirectoryContentIndex.objects.count())
        self.assertEqual(0, ApproximateDirectoryStructureIndex.objects.count())
        self.assertEqual(0, ApproximateResourceContentIndex.objects.count())
        self.assertEqual(0, ExactFileIndex.objects.count())
        self.assertEqual(0, Resource.objects.count())

        scan_data_loc = self.get_test_loc(
            'indexing/scancodeio_wagon-api-20040705.181715.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.loads(f.read())

        indexing_errors = indexing.index_package_files(
            self.package1, scan_data)
        self.assertEqual(0, len(indexing_errors))

        self.assertEqual(11, ApproximateDirectoryContentIndex.objects.count())
        self.assertEqual(
            11, ApproximateDirectoryStructureIndex.objects.count())
        self.assertEqual(2, ApproximateResourceContentIndex.objects.count())
        self.assertEqual(45, ExactFileIndex.objects.count())

        resources = Resource.objects.filter(package=self.package1)
        self.assertEqual(64, len(resources))
        resource_data = [r.to_dict() for r in resources]
        expected_resources_loc = self.get_test_loc(
            'indexing/scancodeio_wagon-api-20040705.181715-expected.json')
        self.check_expected_results(
            resource_data, expected_resources_loc, regen=FIXTURES_REGEN)

    def test_indexing_index_package(self):
        scan_data_loc = self.get_test_loc(
            'indexing/scancodeio_wagon-api-20040705.181715.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.load(f)

        scan_summary_loc = self.get_test_loc(
            'indexing/scancodeio_wagon-api-20040705.181715-summary.json')
        with open(scan_summary_loc, 'rb') as f:
            scan_summary = json.load(f)

        project_extra_data = {
            'md5': 'md5',
            'sha1': 'sha1',
            'sha256': 'sha256',
            'sha512': 'sha512',
            'size': 100,
        }

        # Set up ScannableURI
        scannable_uri = ScannableURI.objects.create(
            uri='https://repo1.maven.org/maven2/maven/wagon-api/20040705.181715/wagon-api-20040705.181715.jar',
            scan_status=ScannableURI.SCAN_COMPLETED,
            package=self.package1
        )

        # Ensure that we do not have any Package data updated, Resources, and fingerprints
        self.assertFalse(self.package1.md5)
        self.assertFalse(self.package1.sha1)
        self.assertFalse(self.package1.sha256)
        self.assertFalse(self.package1.sha512)
        self.assertFalse(self.package1.size)
        self.assertFalse(self.package1.declared_license_expression)
        self.assertFalse(self.package1.copyright)
        self.assertEqual(0, ApproximateDirectoryContentIndex.objects.count())
        self.assertEqual(0, ApproximateDirectoryStructureIndex.objects.count())
        self.assertEqual(0, ApproximateResourceContentIndex.objects.count())
        self.assertEqual(0, ExactFileIndex.objects.count())
        self.assertEqual(0, Resource.objects.count())

        # Run test
        indexing.index_package(
            scannable_uri,
            self.package1,
            scan_data,
            scan_summary,
            project_extra_data,
        )

        # Make sure that Package data is updated
        self.assertEqual(
            'apache-2.0', self.package1.declared_license_expression)
        self.assertEqual(
            'Copyright (c) Apache Software Foundation', self.package1.copyright)
        self.assertEqual('md5', self.package1.md5)
        self.assertEqual('sha1', self.package1.sha1)
        self.assertEqual('sha256', self.package1.sha256)
        self.assertEqual('sha512', self.package1.sha512)
        self.assertEqual(100, self.package1.size)

        for expected_count, model in [
            (11, ApproximateDirectoryContentIndex),
            (2, ApproximateResourceContentIndex),
            (64, Resource),
            (45, ExactFileIndex),
        ]:
            self.assertEqual(
                expected_count,
                model.objects.filter(package=self.package1).count()
            )

    def test_indexing_index_package_dwarf(self):
        scan_data_loc = self.get_test_loc('indexing/get_scan_data_dwarf.json')
        with open(scan_data_loc, 'rb') as f:
            scan_data = json.load(f)

        scan_summary_loc = self.get_test_loc(
            'indexing/scan_summary_dwarf.json')
        with open(scan_summary_loc, 'rb') as f:
            scan_summary = json.load(f)

        project_extra_data = {}

        # Set up ScannableURI
        scannable_uri = ScannableURI.objects.create(
            uri='https://github.com/aboutcode-org/elf-inspector/raw/4333e1601229da87fa88961389d7397af6e027c4/tests/data/dwarf_and_elf/analyze.so.debug',
            scan_status=ScannableURI.SCAN_COMPLETED,
            package=self.package2
        )

        # Run test
        indexing.index_package(
            scannable_uri,
            self.package2,
            scan_data,
            scan_summary,
            project_extra_data,
        )

        package = Package.objects.filter(id=self.package2.id)
        self.assertEqual(1, package.count())

        result = Resource.objects.filter(package=self.package2)
        self.assertEqual(1, result.count())

        extra_data = result.first().extra_data
        expected_extra_data = scan_data["files"][0]["extra_data"]
        self.assertEqual(expected_extra_data, extra_data)
