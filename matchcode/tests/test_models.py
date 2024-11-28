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
        load_resources_from_scan(
            self.get_test_loc("models/match-test.json"), self.test_package4
        )
        index_package_directories(self.test_package4)
        index_package_files_sha1(
            self.test_package4, self.get_test_loc("models/match-test.json")
        )


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
        self.assertTrue(
            "Error('Non-hexadecimal digit found')" in self.test_package1.index_error
        )

    def test_ExactPackageArchiveIndex_single_sha1_single_match(self):
        result = ExactPackageArchiveIndex.match(
            "51d28a27d919ce8690a40f4f335b9d591ceb16e9"
        )
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
        self.assertTrue(
            "Error('Non-hexadecimal digit found')" in self.test_package1.index_error
        )

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

        expected = self.get_test_loc(
            "models/exact-file-matching-standalone-test-results.json"
        )
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
        scan_location = self.get_test_loc(
            "models/directory-matching/async-0.2.9-i.json"
        )
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
            matches = ApproximateDirectoryStructureIndex.match(
                fingerprint=fp, resource=resource
            )
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
        scan_location = self.get_test_loc(
            "models/directory-matching/async-0.2.9-i.json"
        )
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
            matches = ApproximateDirectoryContentIndex.match(
                fingerprint=fp, resource=resource
            )
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
        test_resource1_loc = self.get_test_loc(
            "match/approximate-file-matching/index.js"
        )
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
        ApproximateResourceContentIndex.index(
            "not a fingerprint", resource_path, self.test_package
        )
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
            matches = ApproximateResourceContentIndex.match(
                fingerprint=fp, resource=resource
            )
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
        test_file_loc = self.get_test_loc(
            "match/approximate-file-matching/index-modified.js"
        )
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
            path="adler32.c", name="adler32.c", package=self.test_package
        )
        self.test_resource_snippets = list(
            enumerate(
                [
                    "bbb63027903332f0c41b7b26b9bfb50b",
                    "54cf1197bf1109b4ce2a3455c1c48285",
                    "6d4c7e4377089d1ddcc8c90132ac9730",
                    "1e579e94829907c3d2401db94f9b6df8",
                    "ec89d3e7ac59e858d97ce1ad730f7547",
                    "f3c31ef3249345c3e44c5aea28414dff",
                    "5f1ba9111c115dc88bdc1ceddce789ef",
                    "2f12c505c1e1ec3fa184877c8f1cb838",
                    "a7858f3e1c246064223868c9858f8317",
                    "b7c21f7ebb4abec9169eb533154a5097",
                    "f5139ce5161976ff729a953b8780133d",
                    "c1975628430b6fda66b638481403cca5",
                    "83a4d8bea3052c3bfde90ed3aaba79ac",
                    "3c4df460f6a4817daf8638f3b2009cb9",
                    "3290d45ca11c75f84d72ccfdfcca9515",
                    "bd9b873dd011bb94ba21b449e0886bca",
                    "c51b042fb4aa9dbee729f120d1caa9ad",
                    "3aaa73fb0dbbd0443f7f77d96322b522",
                    "80a509a0b8d81b8167e4bce3bdaf83bf",
                    "4a79d250f6c4aa117bf47244fc0222be",
                    "e49dc8a3fecfe4bb2ef237bb56e85dc8",
                    "e2a16b88325f9b5717b578c9f5207e07",
                    "e28f3e5020594773551a29c39ee4c286",
                    "ae9095ef88ac8288c7514b771ed5ddc8",
                    "01e7fd588d9cd71e30935c597827ce0a",
                    "a54443952d1ce6e731d8980d7b0c714f",
                    "c244ee379eacca3f8799bb94890bd41c",
                    "67913cbdbf8802d7c19a442132ada51b",
                    "b9e5ed3d9a79a4d71d04a6d59589e9c8",
                    "7a10694fe6dadc4f0ff002119d29eac9",
                    "e0fc19761f570e9657324d21b7150a3b",
                    "498885acf844eda1f65af9e746deaff7",
                    "16e774a453769c012ca1e7f3685b4111",
                    "eeb97a9c94bb5c7a8cac39fdea7e7ec2",
                    "5faefb98693a882708b497c90885e84d",
                    "5ca14da77615896d30deb89635c39a53",
                    "628c96760664a4b74d689a398b496e03",
                ]
            )
        )
        for position, fingerprint in self.test_resource_snippets:
            fingerprint = hexstring_to_binarray(fingerprint)
            SnippetIndex.index(
                fingerprint=fingerprint,
                position=position,
                resource=self.test_resource,
                package=self.test_package,
            )

    def test_SnippetIndexTestCase_match(self):
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
        # tuples of positions, value
        test_snippets = list(
            enumerate(
                [
                    "7ed5cafd44fea6cb1e84f519c5a995f3",
                    "9f02df2c2c765ed4b9a60af7f5dc6825",
                    "e643cdd412d46ba058e2be3105b5503d",
                    "090dc3f8751b3c79923d0f2430e1821d",
                    "7b3294908e4bbd6390106fe6d920268f",
                    "4bc9c74165dfd635fee5c3164f2407d8",
                    "b0efbe1869beb1a203a95b18d47ef1e6",
                    "34af742c2a696d0a6bd23e5c96143aa4",
                    "855b779d81fe76ace1afd9cffaaa03b5",
                    "2381aeb9b5cd04dc4f52a1d5e06797e6",
                    "ad117fdd56136e90282025198a1ed5f5",
                    "ce064a8d30610687babebfc3c74f2215",
                    "fe12a3cb12a41359a3f7ea23a8297fca",
                    "1a2f0e65b2d77fb79ed95749083e0356",
                    "945e4a298b851a0fa86853d1fd234d22",
                    "e4cda232353cd78069d7d6a1d11ccfc3",
                    "ab64048739c06b77fbf69f0622a824a0",
                    "fb91eeb4a8b9895e051ec98b649303ff",
                    "a07afc7552c7af2f861a114c19718c12",
                    "c7f68becaa86ac416555dcc13de3f7b6",
                    "7be2af5b15ac4debe2c9233fe3bdf5e2",
                    "e4085cc7580f1f933f524c1742dffc7a",
                    "1bd5c87d7fb5558b1fcd10ef2e0432f8",
                    "fd6a83abd283b4e5ac268f21a2147453",
                    "5a4d0897b9711c02f865d97034338979",
                    "f6bcbd48d1e7ffbb78164cd2660ca0cc",
                    "83ac23f7ee69540adfc64dba65045012",
                    "435d4e0805e1015f58bedb643ce1ad3a",
                    "53b627e84a0fde8342a7c9a5cae51335",
                    "9b34c5bb0ac43bc9f131315c8fa028c3",
                    "8456aa69be29d00cf9dfeb7ae9ccfcdf",
                    "e79c82b208711f5f49f421718ef172c6",
                    "7ac46a9dbd8c68652d347960cc3f640a",
                    "2a6e0b066785d0e1feee19a60d4685f6",
                    "e4c4d99fc98a4cc09f28a291a5212093",
                    "1d64eede99cb6abe784678938f64a12c",
                    "f517d7a22774aeec45c109920b255ae6",
                    "1cdf29098d96d12c8c59acf2304ab1fe",
                    "d2b74ca2087e6e527701c663eefd29bc",
                    "a14974b34a547b1a52af07f590f641d1",
                    "03a6666b52bba552442e73adfbcfccb5",
                    "4cca0e8f81f8fe812eb7861495020ff8",
                    "d9db0fb7358173072bc319707d3e8a33",
                    "2310e0cb39cc317dbaf0bfcca72f0aca",
                    "b6a661bd80f1140a07c511a9ffffb492",
                    "0399fade7fca27b568404b073b2eca1c",
                    "52cfc5757c1f45567ca90a2958a64e22",
                    "f76edad8fa6dc73e843ab228a46ff4aa",
                    "a0877ef600c0b7da27e226e7815bd96d",
                    "dd94cb42ea765f5a3dc74c7116b8112f",
                    "6f62a6a03341268dabc94c8265aab4a3",
                    "d2d90d0a0b8841fdde1e9342ae34e612",
                    "6e8a953486842b17faabbe58aed2d28b",
                    "5a0e16ed296adc58912f12deb8e43cca",
                    "5a04295313ead9f4b5e43a19e57209c9",
                    "ac3d0c06b8855189986c2d4a11be7180",
                    "9f61d026adad0c3ac52ee1db8ebb1761",
                    "163c3e2d2a76b4cffbcec4e7e41340b0",
                    "eb22bfcb167a605f63f1c0e84b4a243c",
                    "c8a523c143b8fecfaecb8788d94f896f",
                    "fd12f7d058933f7def30e7c0575b2512",
                    "cf6dd6d8d3a9fe684606d10e63b3755d",
                    "e989d1b2ef98bfa40bbccc486ed5e965",
                    "498885acf844eda1f65af9e746deaff7",
                    "16e774a453769c012ca1e7f3685b4111",
                    "8963c86e132ae1710491ba552e17d322",
                    "83ee9b95f621713d817fc5ef847a3129",
                    "0afbd0d74b172a8dd08a1b17002400b1",
                    "498901c2be17e44805910ac978c854b5",
                    "58931feaad814e884e3e95bb89bdbf5c",
                    "4a50fed3cb3b2e08962fce9d37ec1faa",
                    "b24f2d699d5c3643f5d30427c4fa9223",
                    "8a576adf5638a477ec06940132a1f583",
                    "b4f309a79529c0103fa356f3552e49bf",
                    "ea41586642fc658861578736941b1786",
                    "b2a8540ad8659f91150764f4bad6bfae",
                    "7a27d2e62d8aad623cfc4f3ceb831ba4",
                    "3aaaa507050eae336d7e870b043cb18c",
                    "603e64a10d74410e4673bf4bddc3a100",
                    "75ad6a60f72125a9e9f0b8bf129731e6",
                ]
            )
        )
        test_snippets = [
            (pos, hexstring_to_binarray(snippet)) for pos, snippet in test_snippets
        ]
        results = SnippetIndex.match(
            fingerprints=test_snippets, resource=test_resource, package=test_package
        )
        expected_fingerprints = [
            hexstring_to_binarray("16e774a453769c012ca1e7f3685b4111"),
            hexstring_to_binarray("498885acf844eda1f65af9e746deaff7"),
        ]
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(self.test_package, result.package)
        fingerprints = [s.fingerprint for s in result.fingerprints]
        self.assertEqual(sorted(expected_fingerprints), sorted(fingerprints))
