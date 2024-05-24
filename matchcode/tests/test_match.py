#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from matchcode.match import APPROXIMATE_DIRECTORY_CONTENT_MATCH
from matchcode.match import APPROXIMATE_DIRECTORY_STRUCTURE_MATCH
from matchcode.match import APPROXIMATE_FILE_MATCH
from matchcode.match import EXACT_FILE_MATCH
from matchcode.match import EXACT_PACKAGE_ARCHIVE_MATCH
from matchcode.match import path_suffixes
from matchcode.match import run_do_match_from_scan
from matchcode.models import ApproximateResourceContentIndex
from matchcode.tests import FIXTURES_REGEN
from matchcode.utils import MatchcodeTestCase
from matchcode.utils import index_package_directories
from matchcode.utils import index_package_files_sha1
from matchcode.utils import index_packages_sha1
from matchcode.utils import load_resources_from_scan
from packagedb.models import Package
from packagedb.models import Resource


class MatchPackagesTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def setUp(self):
        # Execute the superclass' setUp method before creating our own
        # DB objects
        super(MatchPackagesTestCase, self).setUp()

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

        load_resources_from_scan(self.get_test_loc('models/match-test.json'), self.test_package4)
        index_package_directories(self.test_package4)
        index_package_files_sha1(self.test_package4, self.get_test_loc('models/match-test.json'))

        # Add approximate file resource
        self.test_package5, _ = Package.objects.get_or_create(
            filename='inflate.tar.gz',
            sha1='deadfeed',
            type='generic',
            name='inflate',
            version='1.0.0',
            download_url='inflate.com/inflate.tar.gz',
        )
        self.test_resource5, _ = Resource.objects.get_or_create(
            path='inflate.c',
            size=55466,
            package=self.test_package5
        )
        self.test_resource5_fingerprint = '000018fba23a49e4cd40718d1297be719e6564a4'
        ApproximateResourceContentIndex.index(
            self.test_resource5_fingerprint,
            self.test_resource5.path,
            self.test_package5
        )

    def test_do_match_package_archive_match(self):
        input_file = self.get_test_loc('models/match-test.json')
        vc = run_do_match_from_scan(input_file, EXACT_PACKAGE_ARCHIVE_MATCH)
        expected = self.get_test_loc('models/match-test-exact-package-results.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_do_match_approximate_directory_structure_match(self):
        input_file = self.get_test_loc('models/match-test.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('models/match-test-approximate-directory-structure-results.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_do_match_approximate_directory_content_match(self):
        input_file = self.get_test_loc('models/match-test.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('models/match-test-approximate-directory-content-results.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_do_match_package_file_match(self):
        input_file = self.get_test_loc('models/match-test.json')
        vc = run_do_match_from_scan(input_file, EXACT_FILE_MATCH)
        expected = self.get_test_loc('models/match-test-exact-file-results.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_do_match_approximate_package_file_match(self):
        input_file = self.get_test_loc('match/approximate-file-matching/approximate-match-test.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_FILE_MATCH)
        expected = self.get_test_loc('match/approximate-file-matching/approximate-match-test-results.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)


class MatchNestedPackagesTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def setUp(self):
        # Execute the superclass' setUp method before creating our own
        # DB objects
        super(MatchNestedPackagesTestCase, self).setUp()

        self.test_package1, _ = Package.objects.get_or_create(
            filename='plugin-request-2.4.1.tgz',
            sha1='7295749caddd3c52be472eef6623a7b441ed17d6',
            size=7269,
            name='plugin-request',
            version='2.4.1',
            download_url='https://registry.npmjs.org/@umijs/plugin-request/-/plugin-request-2.4.1.tgz',
            type='npm',
        )
        load_resources_from_scan(self.get_test_loc('match/nested/plugin-request-2.4.1-ip.json'), self.test_package1)
        index_package_directories(self.test_package1)

        self.test_package2, _ = Package.objects.get_or_create(
            filename='underscore-1.10.9.tgz',
            sha1='ba7a9cfc15873e67821611503a34a7c26bf7264f',
            size=26569,
            name='underscore',
            version='1.10.9',
            download_url='https://registry.npmjs.org/@types/underscore/-/underscore-1.10.9.tgz',
            type='npm',
        )
        load_resources_from_scan(self.get_test_loc('match/nested/underscore-1.10.9-ip.json'), self.test_package2)
        index_package_directories(self.test_package2)

    def test_do_match_approximate_directory_structure_match(self):
        input_file = self.get_test_loc('match/nested/nested.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/nested/nested-directory-structure-match-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_do_match_approximate_directory_content_match(self):
        input_file = self.get_test_loc('match/nested/nested.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/nested/nested-directory-content-match-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)


class MatchUtilityFunctionsTestCase(MatchcodeTestCase):
    def test_path_suffixes(self):
        suffixes = list(path_suffixes('/foo/bar/baz/qux'))
        expected = ['foo/bar/baz/qux', 'bar/baz/qux', 'baz/qux', 'qux']
        self.assertEqual(expected, suffixes)


class DirectoryMatchingTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def setUp(self):
        super(DirectoryMatchingTestCase, self).setUp()

        self.test_package1, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.3.tgz',
            sha1='aa049c967f999222aa42e14434f0c562ef468241',
            name='abbrev',
            version='1.0.3',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.3.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.3-i.json'), self.test_package1)
        index_package_directories(self.test_package1)

        self.test_package2, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.4.tgz',
            sha1='bd55ae5e413ba1722ee4caba1f6ea10414a59ecd',
            name='abbrev',
            version='1.0.4',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.4.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.4-i.json'), self.test_package2)
        index_package_directories(self.test_package2)

        self.test_package3, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.5.tgz',
            sha1='5d8257bd9ebe435e698b2fa431afde4fe7b10b03',
            name='abbrev',
            version='1.0.5',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.5.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.5-i.json'), self.test_package3)
        index_package_directories(self.test_package3)

        self.test_package4, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.6.tgz',
            sha1='b6d632b859b3fa2d6f7e4b195472461b9e32dc30',
            name='abbrev',
            version='1.0.6',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.6.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.6-i.json'), self.test_package4)
        index_package_directories(self.test_package4)

        self.test_package5, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.7.tgz',
            sha1='5b6035b2ee9d4fb5cf859f08a9be81b208491843',
            name='abbrev',
            version='1.0.7',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.7.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.7-i.json'), self.test_package5)
        index_package_directories(self.test_package5)

        self.test_package6, _ = Package.objects.get_or_create(
            filename='abbrev-1.0.9.tgz',
            sha1='91b4792588a7738c25f35dd6f63752a2f8776135',
            name='abbrev',
            version='1.0.9',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.0.9.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.0.9-i.json'), self.test_package6)
        index_package_directories(self.test_package6)

        self.test_package7, _ = Package.objects.get_or_create(
            filename='abbrev-1.1.0.tgz',
            sha1='d0554c2256636e2f56e7c2e5ad183f859428d81f',
            name='abbrev',
            version='1.1.0',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.1.0.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.1.0-i.json'), self.test_package7)
        index_package_directories(self.test_package7)

        self.test_package8, _ = Package.objects.get_or_create(
            filename='abbrev-1.1.1.tgz',
            sha1='f8f2c887ad10bf67f634f005b6987fed3179aac8',
            name='abbrev',
            version='1.1.1',
            type='npm',
            download_url='https://registry.npmjs.org/abbrev/-/abbrev-1.1.1.tgz',
        )
        load_resources_from_scan(self.get_test_loc('match/directory-matching/abbrev-1.1.1-i.json'), self.test_package8)
        index_package_directories(self.test_package8)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_3(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.3-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.3-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_4(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.4-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.4-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_5(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.5-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.5-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_6(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.6-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.6-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_7(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.7-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.7-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_0_9(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.9-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.9-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_1_0(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.1.0-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.1.0-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_abbrev_1_1_1(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.1.1-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.1.1-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryStructureIndex_get_stdin_3_0_2(self):
        input_file = self.get_test_loc('match/directory-matching/get-stdin-3.0.2-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_STRUCTURE_MATCH)
        expected = self.get_test_loc('match/directory-matching/get-stdin-3.0.2-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_3(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.3-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.3-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_4(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.4-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.4-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_5(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.5-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.5-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_6(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.6-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.6-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_7(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.7-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.7-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_0_9(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.0.9-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.0.9-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_1_0(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.1.0-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.1.0-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_abbrev_1_1_1(self):
        input_file = self.get_test_loc('match/directory-matching/abbrev-1.1.1-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/abbrev-1.1.1-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)

    def test_match_ApproximateDirectoryContentIndex_get_stdin_3_0_2(self):
        input_file = self.get_test_loc('match/directory-matching/get-stdin-3.0.2-i.json')
        vc = run_do_match_from_scan(input_file, APPROXIMATE_DIRECTORY_CONTENT_MATCH)
        expected = self.get_test_loc('match/directory-matching/get-stdin-3.0.2-i-expected.json')
        self.check_codebase(vc, expected, regen=FIXTURES_REGEN)
