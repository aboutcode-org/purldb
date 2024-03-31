#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from commoncode.resource import VirtualCodebase
from packagedb.models import Package
import attr

from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from matchcode_toolkit.fingerprinting import hexstring_to_binarray
from matchcode.management.commands.index_packages import index_package_directories
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import create_halohash_chunks
from matchcode.models import ExactPackageArchiveIndex
from matchcode.models import ExactFileIndex
from matchcode.utils import index_packages_sha1
from matchcode.utils import index_package_files_sha1
from matchcode.utils import load_resources_from_scan
from matchcode.utils import MatchcodeTestCase
from matchcode.tests import FIXTURES_REGEN


EXACT_PACKAGE_ARCHIVE_MATCH = 0
APPROXIMATE_DIRECTORY_STRUCTURE_MATCH = 1
APPROXIMATE_DIRECTORY_CONTENT_MATCH = 2
EXACT_FILE_MATCH = 3


class BaseModelTest(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def setUp(self):
        super(BaseModelTest, self).setUp()

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
        self.test_package1_metadata = self.test_package1.to_dict()

        self.test_package2, _ = Package.objects.get_or_create(
            filename='dojoz-0.4.1-1.jar',
            sha1='ae9d68fd6a29906606c2d9407d1cc0749ef84588',
            md5='508361a1c6273a4c2b8e4945618b509f',
            size=876720,
            name='dojoz',
            version='0.4.1-1',
            download_url='https://repo1.maven.org/maven2/org/zkoss/zkforge/dojoz/0.4.1-1/dojoz-0.4.1-1.jar',
            type='maven',
        )
        self.test_package2_metadata = self.test_package2.to_dict()

        self.test_package3, _ = Package.objects.get_or_create(
            filename='acegi-security-0.51.jar',
            sha1='ede156692b33872f5ee9465b7a06d6b2bc9e5e7f',
            size=176954,
            name='acegi-security',
            version='0.51',
            download_url='https://repo1.maven.org/maven2/acegisecurity/acegi-security/0.51/acegi-security-0.51.jar',
            type='maven'
        )
        self.test_package3_metadata = self.test_package3.to_dict()

        self.test_package4, _ = Package.objects.get_or_create(
            filename='test.tar.gz',
            sha1='deadbeef',
            size=42589,
            name='test',
            version='0.01',
            download_url='https://test.com/test.tar.gz',
            type='maven'
        )
        self.test_package4_metadata = self.test_package4.to_dict()

        # Populate ExactPackageArchiveIndexFingerprint table
        index_packages_sha1()

        # Populate ExactFileIndexFingerprint table
        load_resources_from_scan(self.get_test_loc('models/match-test.json'), self.test_package4)
        index_package_directories(self.test_package4)
        index_package_files_sha1(self.test_package4, self.get_test_loc('models/match-test.json'))


class ExactPackageArchiveIndexModelTestCase(BaseModelTest):
    def test_ExactPackageArchiveIndex_single_sha1_single_match(self):
        result = ExactPackageArchiveIndex.match('51d28a27d919ce8690a40f4f335b9d591ceb16e9')
        result = [r.package.to_dict() for r in result]
        expected = [self.test_package1_metadata]
        self.assertEqual(expected, result)


class ExactFileIndexModelTestCase(BaseModelTest):
    def test_ExactFileIndex_match(self):
        scan_location = self.get_test_loc('models/match-test.json')
        codebase = VirtualCodebase(
            location=scan_location,
            codebase_attributes=dict(
                matches=attr.ib(default=attr.Factory(list))
            ),
            resource_attributes=dict(
                matched_to=attr.ib(default=attr.Factory(list))
            )
        )

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            matches = ExactFileIndex.match(resource.sha1)
            for match in matches:
                p = match.package.to_dict()
                p['match_type'] = 'exact'
                codebase.attributes.matches.append(p)
                resource.matched_to.append(p['purl'])
            resource.save(codebase)

        expected = self.get_test_loc('models/exact-file-matching-standalone-test-results.json')
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)


class ApproximateDirectoryMatchingIndexModelTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        super(MatchcodeTestCase, self).setUp()
        self.test_package1, _ = Package.objects.get_or_create(
            filename='async-0.2.10.tgz',
            sha1='b6bbe0b0674b9d719708ca38de8c237cb526c3d1',
            md5='fd313a0e8cc2343569719e80cd7a67ac',
            size=15772,
            name='async',
            version='0.2.10',
            download_url='https://registry.npmjs.org/async/-/async-0.2.10.tgz',
            type='npm',
        )
        self.test_package1_metadata = self.test_package1.to_dict()
        load_resources_from_scan(self.get_test_loc('models/directory-matching/async-0.2.10.tgz-i.json'), self.test_package1)
        index_package_directories(self.test_package1)

        self.test_package2, _ = Package.objects.get_or_create(
            filename='async-0.2.9.tgz',
            sha1='df63060fbf3d33286a76aaf6d55a2986d9ff8619',
            md5='895ac62ba7c61086cffdd50ab03c0447',
            size=15672,
            name='async',
            version='0.2.9',
            download_url='https://registry.npmjs.org/async/-/async-0.2.9.tgz',
            type='npm',
        )
        self.test_package2_metadata = self.test_package2.to_dict()
        load_resources_from_scan(self.get_test_loc('models/directory-matching/async-0.2.9-i.json'), self.test_package2)
        index_package_directories(self.test_package2)

    def test_ApproximateDirectoryStructureIndex_match_subdir(self):
        scan_location = self.get_test_loc('models/directory-matching/async-0.2.9-i.json')
        vc = VirtualCodebase(
            location=scan_location,
            resource_attributes=dict(packages=attr.ib(default=attr.Factory(list)))
        )
        codebase = compute_codebase_directory_fingerprints(vc)

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            if resource.is_file:
                continue
            fp = resource.extra_data.get('directory_structure', '')
            matches = ApproximateDirectoryStructureIndex.match(fp)
            for match in matches:
                p = match.package.to_dict()
                p['match_type'] = 'approximate-directory-structure'
                resource.packages.append(p)
                resource.save(codebase)

        expected = self.get_test_loc('models/directory-matching/async-0.2.9-i-expected-structure.json')
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)

    def test_ApproximateDirectoryContentIndex_match_subdir(self):
        scan_location = self.get_test_loc('models/directory-matching/async-0.2.9-i.json')
        vc = VirtualCodebase(
            location=scan_location,
            resource_attributes=dict(packages=attr.ib(default=attr.Factory(list)))
        )
        codebase = compute_codebase_directory_fingerprints(vc)

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            if resource.is_file:
                continue
            fp = resource.extra_data.get('directory_content', '')
            matches = ApproximateDirectoryContentIndex.match(fp)
            for match in matches:
                p = match.package.to_dict()
                p['match_type'] = 'approximate-directory-content'
                resource.packages.append(p)
                resource.save(codebase)

        expected = self.get_test_loc('models/directory-matching/async-0.2.9-i-expected-content.json')
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)


class MatchcodeModelUtilsTestCase(MatchcodeTestCase):
    def test_create_halohash_chunks(self):
        fingerprint = '49280e141724c001e1080128621a4210'
        chunk1, chunk2, chunk3, chunk4 = create_halohash_chunks(fingerprint)
        expected_chunk1 = hexstring_to_binarray('49280e14')
        expected_chunk2 = hexstring_to_binarray('1724c001')
        expected_chunk3 = hexstring_to_binarray('e1080128')
        expected_chunk4 = hexstring_to_binarray('621a4210')
        self.assertEqual(expected_chunk1, chunk1)
        self.assertEqual(expected_chunk2, chunk2)
        self.assertEqual(expected_chunk3, chunk3)
        self.assertEqual(expected_chunk4, chunk4)
