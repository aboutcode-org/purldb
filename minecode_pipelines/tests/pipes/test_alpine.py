#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from commoncode.testcase import check_against_expected_json_file
from commoncode.testcase import FileBasedTesting

from minecode_pipelines.pipes import alpine


class AlpineMapperTest(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_parse_apkindex_and_build_package(self):
        index_location = self.get_test_loc("alpine/APKINDEX")
        packages = []
        with open(index_location, encoding="utf-8") as f:
            for pkg in alpine.parse_apkindex(f.read()):
                pd = alpine.build_package(pkg, distro="v3.22", repo="community")
                packages.append(pd.to_dict())
        expected_loc = self.get_test_loc("alpine/expected_packages.json")
        check_against_expected_json_file(packages, expected_loc, regen=False)
