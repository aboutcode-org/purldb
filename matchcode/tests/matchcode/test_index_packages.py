#
# Copyright (c) 2020 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import os

from commoncode.resource import VirtualCodebase

from matchcode.fingerprinting import compute_directory_fingerprints
from matchcode.indexing import _create_virtual_codebase_from_indexable_package
from matchcode.indexing import index_directory_fingerprints
from matchcode.indexing import index_package_archives
from matchcode.indexing import index_package_directories
from matchcode.indexing import index_package_file
from matchcode.management.commands import index_packages
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import create_halohash_chunks
from matchcode.models import hexstring_to_binarray
from matchcode.models import IndexablePackage
from matchcode.models import ExactPackageArchiveIndex
from matchcode.models import ExactFileIndex
from matchcode.models import get_or_create_indexable_package
from matchcode.utils import load_resources_from_scan
from matchcode.utils import MatchcodeTestCase
from packagedb.models import Package
from packagedb.models import Resource


class IndexPackagesTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def setUp(self):
        # Ensure database is empty before adding test packages
        Package.objects.all().delete()

        # Single object, single source
        self.test_package1, _ = Package.objects.get_or_create(
            filename='abbot-0.12.3.jar',
            sha1='51d28a27d919ce8690a40f4f335b9d591ceb16e9',
            md5='38206e62a54b0489fb6baa4db5a06093',
            size=689791,
            name='abbot',
            version='0.12.3',
            download_url='http://repo1.maven.org/maven2/abbot/abbot/0.12.3/abbot-0.12.3.jar',
            type='maven',
        )
        self.scan1 = self.get_test_loc('match/scan1.json')
        load_resources_from_scan(self.scan1, self.test_package1)

    def test_index_packages(self):
        # Ensure ApproximateDirectoryStructureIndex, IndexablePackage,
        # ExactPackageArchiveIndex, and ExactFileIndex tables are empty
        self.assertFalse(ApproximateDirectoryStructureIndex.objects.all())
        self.assertFalse(IndexablePackage.objects.all())
        self.assertFalse(ExactPackageArchiveIndex.objects.all())
        self.assertFalse(ExactFileIndex.objects.all())

        # Populate fingerprint tables from Package and Resources
        package_indexer = index_packages.Command()
        package_indexer.handle()

        # See if the tables have been populated properly
        indexable_packages = IndexablePackage.objects.all()
        self.assertEqual(1, len(indexable_packages))
        indexable_package = indexable_packages[0]
        self.assertEqual(self.test_package1.uuid, indexable_package.uuid)
        self.assertTrue(indexable_package.last_indexed_date)
        self.assertFalse(indexable_package.index_error)

        package_archive_sha1s = ExactPackageArchiveIndex.objects.all()
        self.assertEqual(1, len(package_archive_sha1s))
        package_archive_sha1 = package_archive_sha1s[0]
        expected_sha1 = self.test_package1.sha1
        self.assertEqual(expected_sha1, package_archive_sha1.fingerprint())
        self.assertEqual(indexable_package, package_archive_sha1.package)

        vc = VirtualCodebase(location=self.scan1)
        expected_resources = [r for r in vc.walk(topdown=True) if r.type == 'file']
        package_file_sha1s = ExactFileIndex.objects.all()
        self.assertEqual(len(expected_resources), len(package_file_sha1s))
        for expected_resource, package_file_sha1 in zip(expected_resources, package_file_sha1s):
            self.assertEqual(expected_resource.sha1, package_file_sha1.fingerprint())
            self.assertEqual(indexable_package, package_file_sha1.package)

        directory_structure_fingerprints = ApproximateDirectoryStructureIndex.objects.filter(package=indexable_package).order_by('path')
        # Only one directory should be indexed since we do not create directory
        # fingerprints for directories with only one file in them
        self.assertEqual(1, len(directory_structure_fingerprints))

        result_1 = directory_structure_fingerprints[0]
        self.assertEqual('test', result_1.path)
        self.assertEqual(indexable_package, result_1.package)
        r1_chunk1, r1_chunk2, r1_chunk3, r1_chunk4 = create_halohash_chunks('160440008028c38c24a8038040006040')
        self.assertEqual(r1_chunk1, result_1.chunk1)
        self.assertEqual(r1_chunk2, result_1.chunk2)
        self.assertEqual(r1_chunk3, result_1.chunk3)
        self.assertEqual(r1_chunk4, result_1.chunk4)

    def test_index_packages_index_directory_structure_fingerprints(self):
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)
        index_packages.index_package_directories(indexable_package)
        directory_structure_fingerprints = ApproximateDirectoryStructureIndex.objects.filter(package=indexable_package).order_by('path')
        self.assertEqual(1, len(directory_structure_fingerprints))

        result_1 = directory_structure_fingerprints[0]
        self.assertEqual('test', result_1.path)
        self.assertEqual(indexable_package, result_1.package)

        expected_chunk1 = hexstring_to_binarray('16044000')
        expected_chunk2 = hexstring_to_binarray('8028c38c')
        expected_chunk3 = hexstring_to_binarray('24a80380')
        expected_chunk4 = hexstring_to_binarray('40006040')

        self.assertEqual(expected_chunk1, result_1.chunk1)
        self.assertEqual(expected_chunk2, result_1.chunk2)
        self.assertEqual(expected_chunk3, result_1.chunk3)
        self.assertEqual(expected_chunk4, result_1.chunk4)

    def test_index_package_archives(self):
        # Ensure ExactPackageArchiveIndex table is empty
        self.assertFalse(ExactPackageArchiveIndex.objects.all())

        # Create indexable_package from test_package
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)

        # Load ExactPackageArchiveIndex table
        created = index_package_archives(indexable_package)

        # Check to see if new ExactPackageArchiveIndex was created
        self.assertTrue(created)
        self.assertEqual(1, ExactPackageArchiveIndex.objects.all().count())

        # Ensure the created ExactPackageArchiveIndex indexes the correct checksum and is related to the right Package
        result = ExactPackageArchiveIndex.objects.all()[0]

        self.assertEqual(self.test_package1.sha1, result.fingerprint())
        self.assertEqual(indexable_package, result.package)

    def test_index_package_file(self):
        # Create indexable_package from test_package
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)

        # Ensure ExactFileIndex is empty prior to test
        self.assertFalse(ExactFileIndex.objects.all())

        # Get one resource from test_package1 and index it
        resource = indexable_package.resources.filter(is_file=True)[0]
        created_exact_file_index, _ = index_package_file(resource)

        self.assertTrue(created_exact_file_index)
        self.assertEqual(1, ExactFileIndex.objects.all().count())
        result = ExactFileIndex.objects.all()[0]

        expected_fingerprint = '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8'
        self.assertEqual(expected_fingerprint, result.fingerprint())
        self.assertEqual(indexable_package, result.package)

    def test__create_virtual_codebase_from_indexable_package(self):
        # Create indexable_package from test_package
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)

        vc = _create_virtual_codebase_from_indexable_package(indexable_package)
        expected_vc = VirtualCodebase(location=self.scan1)

        # Ensure that at least the directory structure is the same
        for expected_r, r in zip(expected_vc.walk(), vc.walk()):
            self.assertEqual(expected_r.path, r.path)

    def test_index_directory_fingerprints(self):
        # Create indexable_package from test_package
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)
        vc = _create_virtual_codebase_from_indexable_package(indexable_package)
        vc = compute_directory_fingerprints(vc)

        # Ensure tables are empty prior to indexing
        self.assertFalse(ApproximateDirectoryContentIndex.objects.all())
        self.assertFalse(ApproximateDirectoryStructureIndex.objects.all())

        indexed_adci, indexed_adsi = index_directory_fingerprints(vc, indexable_package)

        # Check to see if anything has been indexed
        self.assertEqual(1, indexed_adci)
        self.assertEqual(1, indexed_adsi)
        self.assertEqual(1, ApproximateDirectoryContentIndex.objects.all().count())
        self.assertEqual(1, ApproximateDirectoryStructureIndex.objects.all().count())

        # Check to see if the correct values have been indexed
        adci = ApproximateDirectoryContentIndex.objects.all()[0]
        adsi = ApproximateDirectoryStructureIndex.objects.all()[0]

        expected_adci_fingerprint = '0000000288212131028101000400403044049614'
        expected_adsi_fingerprint = '00000002160440008028c38c24a8038040006040'
        self.assertEqual(expected_adci_fingerprint, adci.fingerprint())
        self.assertEqual(expected_adsi_fingerprint, adsi.fingerprint())

    def test_index_package_directories(self):
        # Create indexable_package from test_package
        indexable_package, _ = get_or_create_indexable_package(self.test_package1)

        # Ensure tables are empty prior to indexing
        self.assertFalse(ApproximateDirectoryContentIndex.objects.all())
        self.assertFalse(ApproximateDirectoryStructureIndex.objects.all())

        indexed_adci, indexed_adsi = index_package_directories(indexable_package)

        # Check to see if anything has been indexed
        self.assertEqual(1, indexed_adci)
        self.assertEqual(1, indexed_adsi)
        self.assertEqual(1, ApproximateDirectoryContentIndex.objects.all().count())
        self.assertEqual(1, ApproximateDirectoryStructureIndex.objects.all().count())

        # Check to see if the correct values have been indexed
        adci = ApproximateDirectoryContentIndex.objects.all()[0]
        adsi = ApproximateDirectoryStructureIndex.objects.all()[0]

        expected_adci_fingerprint = '0000000288212131028101000400403044049614'
        expected_adsi_fingerprint = '00000002160440008028c38c24a8038040006040'
        self.assertEqual(expected_adci_fingerprint, adci.fingerprint())
        self.assertEqual(expected_adsi_fingerprint, adsi.fingerprint())
