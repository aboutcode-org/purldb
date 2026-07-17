#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from packageurl import PackageURL
from minecode.miners import alpine
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from django.test import TestCase as DjangoTestCase


class AlpineMapperTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_build_packages_metafile_alpine1(self):
        package_url = PackageURL.from_string(
            "pkg:apk/postgresql16-contrib@16.10-r0?arch=x86_64&repo=main&alpine_version=latest-stable"
        )
        apk_download_url = "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/x86_64/postgresql16-contrib-16.10-r0.apk"
        location = self.get_test_loc("alpine/postgresql16-contrib_v3.14-community-armhf")

        result = alpine.build_packages(location, apk_download_url, package_url)
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc("alpine/mapper_postgresql16_contrib_expected.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_metafile_alpine2(self):
        package_url = PackageURL.from_string(
            "pkg:apk/perf-bash-completion@5.10.42-r0?arch=armhf&repo=community&alpine_version=v3.14"
        )

        apk_download_url = "https://dl-cdn.alpinelinux.org/v3.14/community/armhf/perf-bash-completion-5.10.42-r0.apk"
        location = self.get_test_loc("alpine/perf-bash-completion_latest-stable_main_x86_64")

        result = alpine.build_packages(location, apk_download_url, package_url)
        result = [p.to_dict() for p in result]
        expected_loc = self.get_test_loc("alpine/mapper_perf_bash_completion_expected.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)
