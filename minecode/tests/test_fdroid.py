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

from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.miners import fdroid
from minecode.miners import URI
from minecode.tests import FIXTURES_REGEN


class TestFdroidVisitor(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_FdroidPackageRepoVisitor(self):
        uri = 'https://f-droid.org/repo/index-v2.json'
        test_loc = self.get_test_loc('fdroid/index-v2.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _errors = fdroid.FdroidIndexVisitor(uri)

        # this is a non-persistent visitor, lets make sure we dont return any data
        assert not data
        expected_loc = self.get_test_loc(
            'fdroid/index-v2-expected-visit.json',)
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)


class TestFdroidMapper(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages(self):
        with open(self.get_test_loc('fdroid/index-v2-visited.json')) as fdroid_data:
            visited_uris = json.load(fdroid_data)
        visited_uris = [URI(**uri) for uri in visited_uris]
        purl_data = [(u.package_url, json.loads(u.data)) for u in visited_uris]
        packages = []

        for purl, data in purl_data:
            pkgs = list(fdroid.build_packages(purl, data))
            packages.extend(pkgs)

        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'fdroid/index-v2-visited-expected-mapped.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)
