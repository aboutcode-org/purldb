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
from packageurl import PackageURL
from minecode.miners import conda
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from django.test import TestCase as DjangoTestCase


class CondaMapperTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_build_packages_metafile_conda1(self):
        package_url1 = PackageURL.from_string(
            "pkg:conda/numpy@1.11.3?subdir=linux-64&build=py27h1b885b7_8&type=conda"
        )
        package_identifier1 = "numpy-1.11.3-py27h1b885b7_8.conda"
        package_info1 = None
        download_url1 = (
            "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.11.3-py27h1b885b7_8.conda"
        )
        location1 = self.get_test_loc("conda/repodata.json.bz2")

        result = conda.build_packages(
            location1, download_url1, package_info1, package_identifier1, package_url1
        )
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc("conda/mapper_numpy_expected.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_metafile_conda2(self):
        package_url2 = PackageURL.from_string(
            "pkg:conda/conda-forge/sqlalchemy@1.1.13?subdir=linux-64&build=py27hb0a01da_0&type=tar.bz2"
        )
        package_identifier2 = "sqlalchemy-1.1.13-py27hb0a01da_0.tar.bz2"

        with open(self.get_test_loc("conda/package_info_sqlalchemy.json")) as f:
            package_info2 = json.load(f)

        download_url2 = (
            "https://repo.anaconda.com/pkgs/main/linux-64/sqlalchemy-1.1.13-py27hb0a01da_0.tar.bz2"
        )
        location2 = self.get_test_loc("conda/repodata.json.bz2")

        result = conda.build_packages(
            location2, download_url2, package_info2, package_identifier2, package_url2
        )
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc("conda/mapper_sqlalchemy_expected.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)
