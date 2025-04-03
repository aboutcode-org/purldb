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

from django.test import TestCase as DjangoTestCase

from packageurl import PackageURL

from minecode import miners
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class TestCargoMap(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def test_build_packages_with_no_version(self):
        with open(self.get_test_loc("cargo/sam.json")) as cargo_meta:
            metadata = json.load(cargo_meta)
        package_url = PackageURL.from_string("pkg:cargo/sam")
        packages = miners.cargo.build_packages(metadata, package_url)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("cargo/expected-sam.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_with_version(self):
        with open(self.get_test_loc("cargo/sam.json")) as cargo_meta:
            metadata = json.load(cargo_meta)
        package_url = PackageURL.from_string("pkg:cargo/sam@0.3.1")
        packages = miners.cargo.build_packages(metadata, package_url)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("cargo/expected-sam-0.3.1.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)
