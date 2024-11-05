#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import codecs
import gzip
import json
import os
from unittest.case import expectedFailure
from unittest.mock import patch

from debian_inspector import debcon

from minecode import debutils
from minecode.miners import debian
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import mocked_requests_get


class BaseDebianTest(JsonBasedTesting):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def check_objects_expected(self, results, expected_loc, regen=FIXTURES_REGEN):
        """
        Check that an iterable of `results` against the expected results in the
        file at `expected_loc` location.
        """
        results = list(results)
        result = ""
        for item in results:
            if isinstance(item, str):
                result += item.encode("utf-8")
            else:
                if isinstance(item, debcon.Debian822):
                    result += item.__str__()
                else:
                    result += str(item)
            result += "\n"

        if regen:
            with codecs.open(expected_loc, mode="w", encoding="utf-8") as outfile:
                outfile.write(result)

        with codecs.open(expected_loc, mode="rb", encoding="utf-8") as expect:
            expected = expect.read()
            self.assertEqual(expected, result)

    def check_expected_deb822(self, deb_object, expected_loc, regen=FIXTURES_REGEN):
        """Check and compare the Debian `object` with the file at `expected_loc`."""
        result = str(deb_object) + "\n"
        if regen:
            with codecs.open(expected_loc, mode="w", encoding="utf-8") as outfile:
                outfile.write(result)

        with codecs.open(expected_loc, mode="rb", encoding="utf-8") as expect:
            expected = expect.read()
            assert expected == result

    def get_tmp_gz_file(self, loc):
        """Create a .gz file at a temporary location, and return that location."""
        temp_gz_location = self.get_temp_file(extension=".gz")
        with open(loc, "rb") as f:
            file_content = f.read()
        with gzip.open(temp_gz_location, "wb") as f_out:
            f_out.write(file_content)
        return temp_gz_location


class DebutilsTest(BaseDebianTest):
    #################################################################
    # FIXME: THIS IS NOT USED ANYWHERE
    #################################################################

    @expectedFailure
    def test_debcon_get_paragraph_data_from_file_control_basic(self):
        control_file = self.get_test_loc("debian/debutils/control_basic")
        result = debcon.get_paragraph_data_from_file(control_file)
        self.assertEqual("lastfm-python-mirbuild", result["Source"])
        self.assertEqual("python", result["Section"])
        self.assertEqual("optional", result["Priority"])
        self.assertEqual("3.9.1", result["Standards-Version"])
        self.assertTrue("debhelper (>= 5.0.37.2)" in result["Build-Depends"])
        self.assertTrue("cmake" in result["Build-Depends"])

    @expectedFailure
    def test_debcon_get_paragraph_data_from_file_control_invalid(self):
        control_file = self.get_test_loc("debian/debutils/control_invalid")
        result = debcon.get_paragraph_data_from_file(control_file)
        self.assertEqual({}, result)

    @expectedFailure
    def test_debcon_get_paragraph_data_from_file_with_non_existing_path(self):
        control_file = "path_invalid"
        with self.assertRaises(Exception) as context:
            debcon.get_paragraph_data_from_file(control_file)
        self.assertTrue("No such file or directory" in context.exception)

    def test_parse_deb822_dsc(self):
        dsc_file = self.get_test_loc("debian/debutils/3dldf_2.0.3+dfsg-2.dsc")
        result = debcon.get_paragraph_data_from_file(dsc_file)
        expected_loc = self.get_test_loc(
            "debian/debutils/3dldf_2.0.3+dfsg-2.dsc-expected"
        )
        self.check_expected_deb822(result, expected_loc, regen=FIXTURES_REGEN)

    #################################################################

    def test_parse_email(self):
        content = "Debian TeX Maintainers <debian-tex-maint@lists.debian.org>"
        name, email = debutils.parse_email(content)
        self.assertEqual("Debian TeX Maintainers", name)
        self.assertEqual("debian-tex-maint@lists.debian.org", email)

    def test_parse_email_2(self):
        # Space left Purposefully
        content = "        Debian TeX Maintainers "
        name, email = debutils.parse_email(content)
        self.assertEqual("Debian TeX Maintainers", name)
        self.assertEqual(None, email)

    def test_parse_email_3(self):
        # Space left Purposefully
        content = "<       debian-tex-maint@lists.debian.org   >"
        name, email = debutils.parse_email(content)
        self.assertEqual(None, name)
        self.assertEqual("debian-tex-maint@lists.debian.org", email)

    def test_comma_separated(self):
        tags = "implemented-in::perl, role::program, use::converting, works-with::pim"
        result = list(debutils.comma_separated(tags))
        self.assertEqual(
            [
                "implemented-in::perl",
                "role::program",
                "use::converting",
                "works-with::pim",
            ],
            result,
        )


class DebianReleaseTest(BaseDebianTest):
    def test_parse_release(self):
        release_file = self.get_test_loc("debian/release/Release")
        result = list(debian.parse_release(release_file))
        expected_loc = self.get_test_loc("debian/release/Release_expected")
        self.check_expected_deb822(result, expected_loc)

    def test_parse_release_with_md5(self):
        release_file = self.get_test_loc("debian/release/Release_with_md5")
        result = list(debian.parse_release(release_file))
        expected_loc = self.get_test_loc("debian/release/Release_with_md5_expected")
        self.check_expected_deb822(result, expected_loc)

    @expectedFailure
    def test_visit_debian_release(self):
        uri = "http://ftp.debian.org/debian/dists/Debian8.3/Release"
        test_loc = self.get_test_loc("debian/release/visited_Release")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = debian.DebianReleaseVisitor(uri)
        result = json.loads(data)

        release_file = self.get_test_loc("debian/release/visited_Release-expected.json")
        self.check_expected_deb822(result, release_file)


class DebianCopyrightTest(BaseDebianTest):
    # TODO: There is an exception for the current debian copyright parser
    @expectedFailure
    def test_parse_copyright_only_basic(self):
        copyright_file = self.get_test_loc("debian/copyright/basic_copyright")
        copyrights = [info for info in debian.parse_copyright_only(copyright_file)]
        self.assertTrue("Copyright 1998 John Doe <jdoe@example.com>" in copyrights)
        self.assertTrue("Copyright 1998 Jane Doe <packager@example.com>" in copyrights)

    @expectedFailure
    def test_parse_copyright_only_with_incorrect_file(self):
        copyright_file = self.get_test_loc("debian/copyright/invalid_copyright")
        with self.assertRaises(Exception) as context:
            [info for info in debian.parse_copyright_only(copyright_file)]
        self.assertTrue("no paragraphs in input" in context.exception)

    @expectedFailure
    def test_parse_copyright_only_with_incorrect_path(self):
        copyright_file = "path_invalid"
        with self.assertRaises(Exception) as context:
            [info for info in debian.parse_copyright_only(copyright_file)]
        self.assertTrue("No such file or directory" in context.exception)

    @expectedFailure
    def test_parse_copyright_allinfo_basic(self):
        copyright_file = self.get_test_loc("debian/copyright/basic_copyright")
        copyright_data = [
            info for info in debian.parse_copyright_allinfo(copyright_file)
        ]
        expected = [
            {
                "files": ("*",),
                "license": "GPL-2+",
                "copyright": "Copyright 1998 John Doe <jdoe@example.com>",
            },
            {
                "files": ("debian/*",),
                "license": "GPL-2+",
                "copyright": "Copyright 1998 Jane Doe <packager@example.com>",
            },
        ]
        self.assertEqual(expected, copyright_data)

    @expectedFailure
    def test_parse_copyright_allinfo_with_invalid_file(self):
        copyright_file = self.get_test_loc("debian/copyright/invalid_copyright")
        with self.assertRaises(Exception) as context:
            [info for info in debian.parse_copyright_allinfo(copyright_file)]
        self.assertTrue("no paragraphs in input" in context.exception)

    @expectedFailure
    def test_parse_copyright_allinfo_with_incorrect_path(self):
        copyright_file = "path_invalid"
        with self.assertRaises(Exception) as context:
            [info for info in debian.parse_copyright_allinfo(copyright_file)]
        self.assertTrue("No such file or directory" in context.exception)

    @expectedFailure
    def test_parse_license_basic(self):
        copyright_file = self.get_test_loc("debian/copyright/basic_copyright")
        licenses, licensetexts = debian.parse_license(copyright_file)
        expected = {
            "GPL-2+": [
                "This program is free software; you can redistribute it\n"
                "and/or modify it under the terms of the GNU General Public\n"
                "License as published by the Free Software Foundation; either\n"
                "version 2 of the License, or (at your option) any later\n"
                "version.\n\n"
                "This program is distributed in the hope that it will be\n"
                "useful, but WITHOUT ANY WARRANTY; without even the implied\n"
                "warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR\n"
                "PURPOSE.  See the GNU General Public License for more\ndetails.\n\n"
                "You should have received a copy of the GNU General Public\n"
                "License along with this package; if not, write to the Free\n"
                "Software Foundation, Inc., 51 Franklin St, Fifth Floor,\n"
                "Boston, MA  02110-1301 USA\n\n"
                "On Debian systems, the full text of the GNU General Public\n"
                "License version 2 can be found in the file\n"
                "`/usr/share/common-licenses/GPL-2'."
            ]
        }
        self.assertEqual(expected, licenses)
        self.assertEqual([], licensetexts)

    @expectedFailure
    def test_parse_license_with_invalid_file(self):
        copyright_file = self.get_test_loc("debian/copyright/invalid_copyright")
        with self.assertRaises(Exception) as context:
            debian.parse_license(copyright_file)
        self.assertTrue("no paragraphs in input" in context.exception)

    @expectedFailure
    def test_parse_license_with_incorrect_path(self):
        copyright_file = "path_invalid"
        with self.assertRaises(Exception) as context:
            debian.parse_license(copyright_file)
        self.assertTrue("No such file or directory" in context.exception)


class DebianSourcesTest(BaseDebianTest):
    def test_collect_source_packages(self):
        index_file = self.get_test_loc("debian/sources/debian_Sources")
        source_info = [info for info in debian.collect_source_packages(index_file)]
        expected_loc = self.get_test_loc("debian/sources/debian_Sources_visit_expected")
        self.check_objects_expected(source_info, expected_loc, regen=FIXTURES_REGEN)

    def test_collect_source_packages_ubuntu(self):
        index_file = self.get_test_loc("debian/sources/ubuntu_Sources")
        source_info = [info for info in debian.collect_source_packages(index_file)]
        expected_loc = self.get_test_loc("debian/sources/ubuntu_Sources_visit_expected")
        self.check_objects_expected(source_info, expected_loc, regen=FIXTURES_REGEN)

    @expectedFailure
    def test_DebianSourcesVisitor(self):
        uri = (
            "http://ftp.debian.org/debian/dists/jessie-backports/main/source/Sources.gz"
        )
        test_loc = self.get_test_loc("debian/sources/Sources.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = debian.DebianSourcesVisitor(uri)
        expected_loc = self.get_test_loc("debian/sources/Sources.gz-expected.json")
        self.check_expected_uris(list(uris), expected_loc)

    @expectedFailure
    def test_DebianSourcesVisitor_with_invalid_file(self):
        uri = "http://ftp.debian.org/debian/dists/jessie-backports/main/source/invalid_files/Sources.gz"
        test_loc = self.get_test_loc("debian/invalid_files/ls-lR.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _ = debian.DebianSourcesVisitor(uri)
        self.assertEqual(0, len(list(uris)))

    @expectedFailure
    def test_build_source_file_packages(self):
        with open(self.get_test_loc("debian/sources/debian_Sources")) as packs:
            packages = debian.build_source_file_packages(packs.read())
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "debian/sources/debian_Sources_mapped-expected-packages.json"
        )
        self.check_expected_results(packages, expected_loc)


class DebianPackagesTest(BaseDebianTest):
    def test_parse_packages_index(self):
        index_file = self.get_test_loc("debian/packages/debian_Packages")
        package_info = [info for info in debian.parse_packages_index(index_file)]
        expected_loc = self.get_test_loc(
            "debian/packages/debian_Packages-visit-expected.json"
        )
        self.check_objects_expected(package_info, expected_loc, regen=FIXTURES_REGEN)

    @expectedFailure
    def test_parse_packages_from_debian_Packages(self):
        with open(self.get_test_loc("debian/packages/debian_Packages")) as packs:
            packages = debian.parse_packages(packs.read())
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "debian/packages/debian_Packages-expected.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    @expectedFailure
    def test_parse_packages_from_ubuntu_Packages(self):
        with open(self.get_test_loc("debian/packages/ubuntu_Packages")) as packs:
            packages = debian.parse_packages(packs.read())
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "debian/packages/ubuntu_Packages-expected.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    @expectedFailure
    def test_parse_packages_from_installed_status(self):
        with open(self.get_test_loc("debian/status/simple_status")) as packs:
            packages = debian.parse_packages(packs.read())
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "debian/packages/ubuntu_Packages-expected.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)


class DebianLSLRTest(BaseDebianTest):
    def test_DebianDirectoryIndexVisitor_from_debian(self):
        uri = "http://ftp.debian.org/debian/ls-lR.gz"
        test_loc = self.get_test_loc("debian/lslr/ls-lR_debian")
        temp_gz_location = self.get_tmp_gz_file(test_loc)
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, temp_gz_location)
            uris, _, _ = debian.DebianDirectoryIndexVisitor(uri)
        expected_loc = self.get_test_loc("debian/lslr/ls-lR_debian.gz-expected.json")
        self.check_expected_uris(list(uris), expected_loc)

    def test_DebianDirectoryIndexVisitor_from_ubuntu(self):
        uri = "http://archive.ubuntu.com/ubuntu/ls-lR.gz"
        test_loc = self.get_test_loc("debian/lslr/ls-lR_ubuntu")
        temp_gz_location = self.get_tmp_gz_file(test_loc)
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, temp_gz_location)
            uris, _, _ = debian.DebianDirectoryIndexVisitor(uri)
        expected_loc = self.get_test_loc("debian/lslr/ls-lR_ubuntu.gz-expected.json")
        self.check_expected_uris(list(uris), expected_loc)


class DebianDescriptionTest(BaseDebianTest):
    @expectedFailure
    def test_DebianDescriptionVisitor(self):
        uri = "http://ftp.debian.org/debian/pool/main/7/7kaa/7kaa_2.14.3-1.dsc"
        test_loc = self.get_test_loc("debian/dsc/7kaa_2.14.3-1.dsc")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = debian.DebianDescriptionVisitor(uri)
        result = json.loads(data)
        dsc_file = self.get_test_loc("debian/dsc/description_expected.json")
        self.check_expected_deb822(result, dsc_file)

    @expectedFailure
    def test_parse_description(self):
        with open(
            self.get_test_loc("debian/dsc/description.json")
        ) as debian_description_meta:
            metadata = json.load(debian_description_meta)
        packages = debian.parse_description(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("debian/dsc/description-expected.json")
        self.check_expected_results(packages, expected_loc)


class DebianMapperTest(BaseDebianTest):
    @expectedFailure
    def test_get_dependencies(self):
        test = {
            "build1": "build",
            "build2": "build2",
            "build3": "buildnot",
        }
        keys = ["build1", "build2"]
        result = debian.get_dependencies(test, keys)
        self.assertEqual(2, len(result))
        self.assertEqual("build", result[0].purl)
        self.assertEqual(None, result[0].requirement)
        self.assertEqual("build2", result[1].purl)
        self.assertEqual(None, result[1].requirement)

    def test_get_programming_language(self):
        tags = [
            "role::program",
            "implemented-in::perl",
            "use::converting",
            "works-with::pim",
        ]
        result = debian.get_programming_language(tags)
        self.assertEqual("perl", result)
