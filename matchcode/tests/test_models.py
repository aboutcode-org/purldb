#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

import attr
from commoncode.resource import VirtualCodebase
from licensedcode.spans import Span
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from matchcode_toolkit.fingerprinting import get_file_fingerprint_hashes
from matchcode_toolkit.fingerprinting import hexstring_to_binarray

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ApproximateResourceContentIndex
from matchcode.models import ExactFileIndex
from matchcode.models import ExactPackageArchiveIndex
from matchcode.models import SnippetIndex
from matchcode.models import create_halohash_chunks
from matchcode.tests import FIXTURES_REGEN
from matchcode.utils import MatchcodeTestCase
from matchcode.utils import index_package_directories
from matchcode.utils import index_package_files_sha1
from matchcode.utils import index_packages_sha1
from matchcode.utils import load_resources_from_scan
from packagedb.models import Package
from packagedb.models import Resource

EXACT_PACKAGE_ARCHIVE_MATCH = 0
APPROXIMATE_DIRECTORY_STRUCTURE_MATCH = 1
APPROXIMATE_DIRECTORY_CONTENT_MATCH = 2
EXACT_FILE_MATCH = 3


class BaseModelTest(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.test_package1, _ = Package.objects.get_or_create(
            filename="abbot-0.12.3.jar",
            sha1="51d28a27d919ce8690a40f4f335b9d591ceb16e9",
            md5="38206e62a54b0489fb6baa4db5a06093",
            size=689791,
            name="abbot",
            version="0.12.3",
            download_url="http://repo1.maven.org/maven2/abbot/abbot/0.12.3/abbot-0.12.3.jar",
            type="maven",
        )
        self.test_package1_metadata = self.test_package1.to_dict()

        self.test_package2, _ = Package.objects.get_or_create(
            filename="dojoz-0.4.1-1.jar",
            sha1="ae9d68fd6a29906606c2d9407d1cc0749ef84588",
            md5="508361a1c6273a4c2b8e4945618b509f",
            size=876720,
            name="dojoz",
            version="0.4.1-1",
            download_url="https://repo1.maven.org/maven2/org/zkoss/zkforge/dojoz/0.4.1-1/dojoz-0.4.1-1.jar",
            type="maven",
        )
        self.test_package2_metadata = self.test_package2.to_dict()

        self.test_package3, _ = Package.objects.get_or_create(
            filename="acegi-security-0.51.jar",
            sha1="ede156692b33872f5ee9465b7a06d6b2bc9e5e7f",
            size=176954,
            name="acegi-security",
            version="0.51",
            download_url="https://repo1.maven.org/maven2/acegisecurity/acegi-security/0.51/acegi-security-0.51.jar",
            type="maven",
        )
        self.test_package3_metadata = self.test_package3.to_dict()

        self.test_package4, _ = Package.objects.get_or_create(
            filename="test.tar.gz",
            sha1="deadbeef",
            size=42589,
            name="test",
            version="0.01",
            download_url="https://test.com/test.tar.gz",
            type="maven",
        )
        self.test_package4_metadata = self.test_package4.to_dict()

        # Populate ExactPackageArchiveIndexFingerprint table
        index_packages_sha1()

        # Populate ExactFileIndexFingerprint table
        load_resources_from_scan(self.get_test_loc("models/match-test.json"), self.test_package4)
        index_package_directories(self.test_package4)
        index_package_files_sha1(self.test_package4, self.get_test_loc("models/match-test.json"))


class ExactPackageArchiveIndexModelTestCase(BaseModelTest):
    def test_ExactPackageArchiveIndex_index(self):
        sha1 = "b6bbe0b067469d719708ca38de5c237cb526c3d2"
        epai, created = ExactPackageArchiveIndex.index(sha1, self.test_package1)
        self.assertTrue(created)
        self.assertEqual(sha1, epai.fingerprint())

    def test_ExactPackageArchiveIndex_index_of_existing_sha1(self):
        sha1 = "b6bbe0b067469d719708ca38de5c237cb526c3d2"
        # create
        _epai, _created = ExactPackageArchiveIndex.index(sha1, self.test_package1)
        # create again
        epai, created = ExactPackageArchiveIndex.index(sha1, self.test_package1)
        self.assertFalse(created)
        self.assertEqual(sha1, epai.fingerprint())

    def test_ExactPackageArchiveIndex_index_of_invalid_sha1(self):
        ExactPackageArchiveIndex.index("not a sha1", self.test_package1)
        self.assertTrue("Error('Non-hexadecimal digit found')" in self.test_package1.index_error)

    def test_ExactPackageArchiveIndex_single_sha1_single_match(self):
        result = ExactPackageArchiveIndex.match("51d28a27d919ce8690a40f4f335b9d591ceb16e9")
        result = [r.package.to_dict() for r in result]
        expected = [self.test_package1_metadata]
        self.assertEqual(expected, result)


class ExactFileIndexModelTestCase(BaseModelTest):
    def test_ExactFileIndex_index(self):
        # Test index
        sha1 = "b6bbe0b067469d719708ca38de5c237cb526c3d2"
        efi, created = ExactFileIndex.index(sha1, self.test_package1)
        self.assertTrue(created)
        self.assertEqual(sha1, efi.fingerprint())

        # Test index of existing sha1
        efi, created = ExactFileIndex.index(sha1, self.test_package1)
        self.assertFalse(created)
        self.assertEqual(sha1, efi.fingerprint())

        # Test index of invalid sha1
        ExactFileIndex.index("not a sha1", self.test_package1)
        self.assertTrue("Error('Non-hexadecimal digit found')" in self.test_package1.index_error)

    def test_ExactFileIndex_match(self):
        scan_location = self.get_test_loc("models/match-test.json")
        codebase = VirtualCodebase(
            location=scan_location,
            codebase_attributes=dict(matches=attr.ib(default=attr.Factory(list))),
            resource_attributes=dict(matched_to=attr.ib(default=attr.Factory(list))),
        )

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            matches = ExactFileIndex.match(resource.sha1)
            for match in matches:
                p = match.package.to_dict()
                p["match_type"] = "exact"
                codebase.attributes.matches.append(p)
                resource.matched_to.append(p["purl"])
            resource.save(codebase)

        expected = self.get_test_loc("models/exact-file-matching-standalone-test-results.json")
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)


class ApproximateDirectoryMatchingIndexModelTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        super(MatchcodeTestCase, self).setUp()
        self.test_package1, _ = Package.objects.get_or_create(
            filename="async-0.2.10.tgz",
            sha1="b6bbe0b0674b9d719708ca38de8c237cb526c3d1",
            md5="fd313a0e8cc2343569719e80cd7a67ac",
            size=15772,
            name="async",
            version="0.2.10",
            download_url="https://registry.npmjs.org/async/-/async-0.2.10.tgz",
            type="npm",
        )
        self.test_package1_metadata = self.test_package1.to_dict()
        load_resources_from_scan(
            self.get_test_loc("models/directory-matching/async-0.2.10.tgz-i.json"),
            self.test_package1,
        )
        index_package_directories(self.test_package1)

        self.test_package2, _ = Package.objects.get_or_create(
            filename="async-0.2.9.tgz",
            sha1="df63060fbf3d33286a76aaf6d55a2986d9ff8619",
            md5="895ac62ba7c61086cffdd50ab03c0447",
            size=15672,
            name="async",
            version="0.2.9",
            download_url="https://registry.npmjs.org/async/-/async-0.2.9.tgz",
            type="npm",
        )
        self.test_package2_metadata = self.test_package2.to_dict()
        load_resources_from_scan(
            self.get_test_loc("models/directory-matching/async-0.2.9-i.json"),
            self.test_package2,
        )
        index_package_directories(self.test_package2)

    def test_ApproximateDirectoryStructureIndex_index(self):
        # Test index
        fingerprint = "000018fad23a49e4cd40718d1297be719e6564a4"
        resource_path = "foo/bar"
        adsi, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package1
        )
        self.assertTrue(created)
        self.assertEqual(fingerprint, adsi.fingerprint())

        # Test index of existing fingerprint
        adsi, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package1
        )
        self.assertFalse(created)
        self.assertEqual(fingerprint, adsi.fingerprint())

        # Test index of invalid fingerprint
        ApproximateResourceContentIndex.index(
            "not a fingerprint", resource_path, self.test_package1
        )
        self.assertTrue(
            "ValueError: invalid literal for int() with base 16: 'not a fi'"
            in self.test_package1.index_error
        )

    def test_ApproximateDirectoryStructureIndex_match_subdir(self):
        scan_location = self.get_test_loc("models/directory-matching/async-0.2.9-i.json")
        vc = VirtualCodebase(
            location=scan_location,
            resource_attributes=dict(packages=attr.ib(default=attr.Factory(list))),
        )
        codebase = compute_codebase_directory_fingerprints(vc)

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            if resource.is_file:
                continue
            fp = resource.extra_data.get("directory_structure", "")
            matches = ApproximateDirectoryStructureIndex.match(fingerprint=fp, resource=resource)
            for match in matches:
                p = match.package.to_dict()
                p["match_type"] = "approximate-directory-structure"
                resource.packages.append(p)
                resource.save(codebase)

        expected = self.get_test_loc(
            "models/directory-matching/async-0.2.9-i-expected-structure.json"
        )
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)

    def test_ApproximateDirectoryContentIndex_index(self):
        # Test index
        fingerprint = "000018fad23a49e4cd40718d1297be719e6564a4"
        resource_path = "foo/bar"
        adci, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package1
        )
        self.assertTrue(created)
        self.assertEqual(fingerprint, adci.fingerprint())

        # Test index of existing fingerprint
        adci, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package1
        )
        self.assertFalse(created)
        self.assertEqual(fingerprint, adci.fingerprint())

        # Test index of invalid fingerprint
        ApproximateResourceContentIndex.index(
            "not a fingerprint", resource_path, self.test_package1
        )
        self.assertTrue(
            "ValueError: invalid literal for int() with base 16: 'not a fi'"
            in self.test_package1.index_error
        )

    def test_ApproximateDirectoryContentIndex_match_subdir(self):
        scan_location = self.get_test_loc("models/directory-matching/async-0.2.9-i.json")
        vc = VirtualCodebase(
            location=scan_location,
            resource_attributes=dict(packages=attr.ib(default=attr.Factory(list))),
        )
        codebase = compute_codebase_directory_fingerprints(vc)

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            if resource.is_file:
                continue
            fp = resource.extra_data.get("directory_content", "")
            matches = ApproximateDirectoryContentIndex.match(fingerprint=fp, resource=resource)
            for match in matches:
                p = match.package.to_dict()
                p["match_type"] = "approximate-directory-content"
                resource.packages.append(p)
                resource.save(codebase)

        expected = self.get_test_loc(
            "models/directory-matching/async-0.2.9-i-expected-content.json"
        )
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)


class ApproximateResourceMatchingIndexModelTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        super(MatchcodeTestCase, self).setUp()

        # Add approximate file resource
        self.test_package, _ = Package.objects.get_or_create(
            filename="inflate.tar.gz",
            sha1="deadfeed",
            type="generic",
            name="inflate",
            version="1.0.0",
            download_url="inflate.com/inflate.tar.gz",
        )
        self.test_resource, _ = Resource.objects.get_or_create(
            path="inflate.c", name="inflate.c", size=55466, package=self.test_package
        )
        self.test_resource_fingerprint = "000018fba23a49e4cd40718d1297be719e6564a4"
        ApproximateResourceContentIndex.index(
            self.test_resource_fingerprint, self.test_resource.path, self.test_package
        )

        # Add approximate file resource
        self.test_package1, _ = Package.objects.get_or_create(
            filename="deep-equal-1.0.1.tgz",
            sha1="f5d260292b660e084eff4cdbc9f08ad3247448b5",
            type="npm",
            name="deep-equal",
            version="1.0.1",
            download_url="https://registry.npmjs.org/deep-equal/-/deep-equal-1.0.1.tgz",
        )
        self.test_resource1, _ = Resource.objects.get_or_create(
            path="package/index.js",
            name="index",
            extension="js",
            package=self.test_package1,
        )
        test_resource1_loc = self.get_test_loc("match/approximate-file-matching/index.js")
        fingerprints = get_file_fingerprint_hashes(test_resource1_loc)
        self.test_resource1_fingerprint = fingerprints["halo1"]
        ApproximateResourceContentIndex.index(
            self.test_resource1_fingerprint,
            self.test_resource1.path,
            self.test_package1,
        )

    def test_ApproximateResourceContentIndex_index(self):
        # Test index
        fingerprint = "000018fba23a39e4cd40718d1297be719e6564a4"
        resource_path = "foo/bar"
        adci, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package
        )
        self.assertTrue(created)
        self.assertEqual(fingerprint, adci.fingerprint())

        # Test index of existing fingerprint
        adci, created = ApproximateResourceContentIndex.index(
            fingerprint, resource_path, self.test_package
        )
        self.assertFalse(created)
        self.assertEqual(fingerprint, adci.fingerprint())

        # Test index of invalid fingerprint
        ApproximateResourceContentIndex.index("not a fingerprint", resource_path, self.test_package)
        self.assertTrue(
            "ValueError: invalid literal for int() with base 16: 'not a fi'"
            in self.test_package.index_error
        )

    def test_ApproximateResourceContentIndex_match(self):
        scan_location = self.get_test_loc(
            "match/approximate-file-matching/approximate-match-test.json"
        )
        codebase = VirtualCodebase(
            location=scan_location,
            resource_attributes=dict(packages=attr.ib(default=attr.Factory(list))),
        )

        # populate codebase with match results
        for resource in codebase.walk(topdown=True):
            if not (fp := resource.halo1):
                continue
            matches = ApproximateResourceContentIndex.match(fingerprint=fp, resource=resource)
            for match in matches:
                p = match.package.to_dict()
                p["match_type"] = "approximate-resource-content"
                resource.packages.append(p)
                resource.save(codebase)

        expected = self.get_test_loc(
            "match/approximate-file-matching/approximate-match-model-test-results.json"
        )
        self.check_codebase(codebase, expected, regen=FIXTURES_REGEN)

    def test_ApproximateResourceContentIndex_match_deep_equals(self):
        test_file_loc = self.get_test_loc("match/approximate-file-matching/index-modified.js")
        fingerprints = get_file_fingerprint_hashes(test_file_loc)
        fp = fingerprints["halo1"]
        matches = ApproximateResourceContentIndex.match(fp)
        results = [match.package.to_dict() for match in matches]
        expected_results_loc = self.get_test_loc(
            "match/approximate-file-matching/index-modified.js-expected.json"
        )
        self.check_expected_results(results, expected_results_loc, regen=FIXTURES_REGEN)


class MatchcodeModelUtilsTestCase(MatchcodeTestCase):
    def test_create_halohash_chunks(self):
        fingerprint = "49280e141724c001e1080128621a4210"
        chunk1, chunk2, chunk3, chunk4 = create_halohash_chunks(fingerprint)
        expected_chunk1 = hexstring_to_binarray("49280e14")
        expected_chunk2 = hexstring_to_binarray("1724c001")
        expected_chunk3 = hexstring_to_binarray("e1080128")
        expected_chunk4 = hexstring_to_binarray("621a4210")
        self.assertEqual(expected_chunk1, chunk1)
        self.assertEqual(expected_chunk2, chunk2)
        self.assertEqual(expected_chunk3, chunk3)
        self.assertEqual(expected_chunk4, chunk4)


class SnippetIndexTestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        super(MatchcodeTestCase, self).setUp()

        # Add approximate file resource
        self.test_package1, _ = Package.objects.get_or_create(
            filename="deep-equal-1.0.1.tgz",
            sha1="f5d260292b660e084eff4cdbc9f08ad3247448b5",
            type="npm",
            name="deep-equal",
            version="1.0.1",
            download_url="https://registry.npmjs.org/deep-equal/-/deep-equal-1.0.1.tgz",
        )
        self.test_resource1, _ = Resource.objects.get_or_create(
            path="package/index.js",
            name="index",
            extension="js",
            package=self.test_package1,
        )
        test_resource1_loc = self.get_test_loc("match/approximate-file-matching/index.js")
        fingerprints = get_file_fingerprint_hashes(test_resource1_loc, include_ngrams=True)

        self.test_resource1_snippets = fingerprints["snippets"]
        for snippet in self.test_resource1_snippets:
            fingerprint = snippet["snippet"]
            position = snippet["position"]
            SnippetIndex.index(
                fingerprint,
                position,
                self.test_resource1,
                self.test_package1,
            )

        self.test_resource2, _ = Resource.objects.get_or_create(
            path="package/index-2.js",
            name="index-2",
            extension="js",
            package=self.test_package1,
        )
        test_resource2_loc = self.get_test_loc("match/approximate-file-matching/index-2.js")
        fingerprints2 = get_file_fingerprint_hashes(test_resource2_loc, include_ngrams=True)

        self.test_resource2_snippets = fingerprints2["snippets"]
        for snippet in self.test_resource2_snippets:
            fingerprint = snippet["snippet"]
            position = snippet["position"]
            SnippetIndex.index(
                fingerprint,
                position,
                self.test_resource2,
                self.test_package1,
            )

        self.test_package2, _ = Package.objects.get_or_create(
            filename="inflate.tgz",
            sha1="beef",
            type="github",
            name="inflate",
            version="0.0.2",
            download_url="https://download.c",
        )
        self.test_resource3, _ = Resource.objects.get_or_create(
            path="inflate.c",
            name="inflate",
            extension="c",
            package=self.test_package2,
        )
        test_resource3_loc = self.get_test_loc("match/approximate-file-matching/inflate.c")
        fingerprints3 = get_file_fingerprint_hashes(test_resource3_loc, include_ngrams=True)

        self.test_resource3_snippets = fingerprints3["snippets"]
        for snippet in self.test_resource3_snippets:
            fingerprint = snippet["snippet"]
            position = snippet["position"]
            SnippetIndex.index(
                fingerprint,
                position,
                self.test_resource3,
                self.test_package2,
            )

        self.test_resource4, _ = Resource.objects.get_or_create(
            path="inflate-mod2.c",
            name="inflate-mod2",
            extension="c",
            package=self.test_package2,
        )
        test_resource4_loc = self.get_test_loc("match/approximate-file-matching/inflate-mod2.c")
        fingerprints4 = get_file_fingerprint_hashes(test_resource4_loc, include_ngrams=True)

        self.test_resource4_snippets = fingerprints4["snippets"]
        for snippet in self.test_resource4_snippets:
            fingerprint = snippet["snippet"]
            position = snippet["position"]
            SnippetIndex.index(
                fingerprint,
                position,
                self.test_resource4,
                self.test_package2,
            )

        self.test_resource5, _ = Resource.objects.get_or_create(
            path="inflate-mod3.c",
            name="inflate-mod3",
            extension="c",
            package=self.test_package2,
        )
        test_resource5_loc = self.get_test_loc("match/approximate-file-matching/inflate-mod3.c")
        fingerprints5 = get_file_fingerprint_hashes(test_resource5_loc, include_ngrams=True)

        self.test_resource5_snippets = fingerprints5["snippets"]
        for snippet in self.test_resource5_snippets:
            fingerprint = snippet["snippet"]
            position = snippet["position"]
            SnippetIndex.index(
                fingerprint,
                position,
                self.test_resource5,
                self.test_package2,
            )

    def test_SnippetIndexTestCase_match(self):
        test_file_loc = self.get_test_loc("match/approximate-file-matching/index-modified.js")
        test_package, _ = Package.objects.get_or_create(
            filename="test_package.tar.gz",
            sha1="beefbeef",
            type="generic",
            name="test_package",
            version="1.0.0",
            download_url="test_package.com/test_package.tar.gz",
        )
        test_resource, _ = Resource.objects.get_or_create(
            path="zutil.c", name="zutil.c", package=test_package
        )
        fingerprints = get_file_fingerprint_hashes(test_file_loc)
        snippets = fingerprints["snippets"]
        results = SnippetIndex.match(fingerprints=snippets)
        assert len(results) == 1
        result = results[0]
        assert result.package == self.test_package1
        fingerprints = [s.fingerprint.hex() for s in result.fingerprints]
        expected_fingerprints = [
            "0fc763be3b308fae5a52001e7efc4090",
            "10d99030ca0909ccb3a32c9d635f3253",
            "1e46a0e582eef335fba50714141c27dc",
            "1f4c27fe6d93ac4f1d9b60f79475dd3c",
            "2142ebacc010c03395ea0a7154ef7541",
            "26259a72175bb019ea58bd86ea604991",
            "2bee81b8c34d62fc9a12a4a62721f9f3",
            "2d8743da741362e5e0841bb5379914bb",
            "2e2e4e5e18477aaee1125a2cb12b6485",
            "30704943d266bdb18eafc677873e9822",
            "32a2a558e27c87650e5162202f0196df",
            "3b15b5f5bda3c9f4a9805e250c5798aa",
            "3c09ebac8c21673d983a93e00cf6c95a",
            "414eb6dbc410b7db13c5261d38d2415c",
            "4ce5bee5d7ed3434eb68d5d80a4dab22",
            "5014a7286f940ecb7cb514a08fe30d39",
            "522023f5ce1d48f65e947821132122e9",
            "535db56c916b267cb5f8935b46c8c56b",
            "5794339ebf262545567070edc0d53303",
            "5f7c78add17179b391825516483c2d31",
            "5f9344fe7b73af75892066cad7501987",
            "66a0f9a75b66e53c082bb2df58dbf328",
            "6786630e87ed9f1fcd0f2de19d69132f",
            "6c852b29e58a20bdbffdd3c3d39de4ca",
            "6f895585fb5f35be5ac4e7d3365d2b7e",
            "721404f59a9fd12f820e3484c32c8ee7",
            "73881c41e7004a29746ad40052537473",
            "858afa72b0b2085ad5130e9882fdeedc",
            "86d683c2d96246662570b512fce610ba",
            "88dbb2466f4158774dd1445697bf08cd",
            "8b8902668a5cce6833cc5ced43db899c",
            "938d957a337ceacb3de0ae8bcda9e2de",
            "940e3b3b98650d3ed71ec6e1363f4c61",
            "95a0911958836ece77ef2d5d2cefca23",
            "95d4dd4aeadf8aaadac0bb640bba4e71",
            "a3f09e6beedcded219df8593450b03d3",
            "a82c31729d82b8adff02c273ac0b07eb",
            "a8860e6ff83c23f994724757cd0b6eb3",
            "aa55727f4d7380bc04244accf9d0a577",
            "aabe725b62af9dde68c43239cf4c1ea8",
            "ac02d66ba0ae0ecd3153c1020f844b52",
            "af7cfcc143fa9f4453f50d8a9aade620",
            "b48c0453e4a625cda1878c5460bb926c",
            "ba0d298d9bab393b33121e3990f4c306",
            "bc031cbb660864a64b3d9ac33c4bc4a7",
            "bdb40a475b3b0a5fb530005408637b6b",
            "cb46aa07c44b27e4f1a78740bdf3617a",
            "cdfa7520a8b905b0f7d3cdcff1ef9b32",
            "cfbef533ed1368ce056ab096ba615138",
            "d0cd21fe86af6e9486d02b192c616d16",
            "d1f334cf76e48d847f4f5767717dba77",
            "e25b8cc23b00525615a64b2f1529631c",
            "e27959753347f81acd578caffa57966d",
            "eb85e29dd6d2085bd7becd81edbec443",
            "ed07fae33a9889fc6538086e96cc41a3",
            "ed52227dfd8f9ef7c09d7b6420c6802d",
            "f889ec2655204b44d46003190ca74553",
            "ff0f5b8aba10817a04493b277619db54",
        ]

        assert sorted(fingerprints) == sorted(expected_fingerprints)

    def test_SnippetIndexTestCase_match_resource(self):
        test_file_loc = self.get_test_loc("match/approximate-file-matching/inflate-mod.c")
        fingerprints = get_file_fingerprint_hashes(test_file_loc)
        snippets = fingerprints["snippets"]
        matches = SnippetIndex.match_resources(fingerprints=snippets)
        assert len(matches) == 3
        match = matches[0]
        assert match.resource == self.test_resource3
        assert match.package == self.test_package2
        expected_detections = [Span(0, 651), Span(659, 774), Span(780, 6093)]
        assert match.match_detections == expected_detections
        assert match.similarity == 0.9286452947259566

    def test_SnippetIndexTestCase_match_resource_return_only_top_match(self):
        test_file_loc = self.get_test_loc("match/approximate-file-matching/inflate-mod.c")
        fingerprints = get_file_fingerprint_hashes(test_file_loc)
        snippets = fingerprints["snippets"]
        matches = SnippetIndex.match_resources(
            fingerprints=snippets,
            top=1,
        )
        assert len(matches) == 1
        match = matches[0]
        assert match.resource == self.test_resource3
        assert match.package == self.test_package2
        expected_detections = [Span(0, 651), Span(659, 774), Span(780, 6093)]
        assert match.match_detections == expected_detections
        assert match.similarity == 0.9286452947259566

    def test_SnippetIndex_match_resources_match_to_resource_with_less_duplicates(self):
        test_file_loc = self.get_test_loc("match/approximate-file-matching/index-modified.js")
        test_package, _ = Package.objects.get_or_create(
            filename="test_package.tar.gz",
            sha1="beefbeef",
            type="generic",
            name="test_package",
            version="1.0.0",
            download_url="test_package.com/test_package.tar.gz",
        )
        test_resource, _ = Resource.objects.get_or_create(
            path="zutil.c", name="zutil.c", package=test_package
        )
        fingerprints = get_file_fingerprint_hashes(test_file_loc)
        snippets = fingerprints["snippets"]
        matches = SnippetIndex.match_resources(
            fingerprints=snippets,
        )
        assert len(matches) == 2
        match = matches[0]
        assert match.resource == self.test_resource1
        assert match.package == self.test_package1
        expected_match_detections = [Span(0, 153), Span(167, 398)]
        assert match.match_detections == expected_match_detections
        assert match.similarity == 0.9206349206349206
