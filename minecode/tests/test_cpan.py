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
from collections import OrderedDict
from unittest.mock import patch

from minecode import mappers
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import mocked_requests_get
from minecode.visitors import cpan


class CpanVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def test_metacpanauthorurlvisitors(self):
        uri = "https://fastapi.metacpan.org/author/_search?q=email:a*&size=5000"
        test_loc = self.get_test_loc("cpan/search_email_a.json")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = cpan.CpanModulesVisitors(uri)
        expected_loc = self.get_test_loc("cpan/expected_search_email_a.json")
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_release_search_from_author_visitors(self):
        uri = "https://fastapi.metacpan.org/release/_search?q=author:ABERNDT&size=5000"
        test_loc = self.get_test_loc("cpan/release_from_author_ABERNDT.json")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = cpan.CpanModulesVisitors(uri)
        expected_loc = self.get_test_loc(
            "cpan/expected_release_from_author_ABERNDT.json"
        )
        self.check_expected_results(data, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_html_modules(self):
        uri = "http://www.cpan.org/modules/01modules.index.html"
        test_loc = self.get_test_loc("cpan/Modules on CPAN alphabetically.html")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = cpan.CpanModulesVisitors(uri)
        expected_loc = self.get_test_loc("cpan/expected_html_modules.json")
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_html_files(self):
        uri = "http://www.cpan.org/authors/id/L/LD/LDS/"
        test_loc = self.get_test_loc("cpan/Index_of_authors_id_L_LD_LDS.html")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = cpan.CpanProjectHTMLVisitors(uri)
        expected_loc = self.get_test_loc("cpan/expected_html_files.json")
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_readme_file(self):
        uri = "http://www.cpan.org/authors/id/A/AM/AMIRITE/Mojolicious-Plugin-Nour-Config-0.09.readme"
        test_loc = self.get_test_loc("cpan/Mojolicious-Plugin-Nour-Config-0.09.readme")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = cpan.CpanReadmeVisitors(uri)
        result = json.loads(data, object_pairs_hook=OrderedDict)
        expected_file = self.get_test_loc("cpan/expected_readme.json")
        self.check_expected_results(result, expected_file, regen=FIXTURES_REGEN)


class CpanMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def test_build_from_release_search_json(self):
        with open(self.get_test_loc("cpan/release_search.json")) as cpan_metadata:
            metadata = cpan_metadata.read()
        packages = mappers.cpan.build_packages_from_release_json(
            metadata,
            "https://fastapi.metacpan.org/release/_search?q=author:ABERNDT&size=5000",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("cpan/expected_release_search.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_from_release_search_json2(self):
        with open(
            self.get_test_loc("cpan/MIYAGAWA_author_release_search.json")
        ) as cpan_metadata:
            metadata = cpan_metadata.read()
        packages = mappers.cpan.build_packages_from_release_json(
            metadata,
            "https://fastapi.metacpan.org/release/_search?q=author:MIYAGAWA&size=5000",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "cpan/expected_release_search_author_MIYAGAWA.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_metafile_from_yaml(self):
        with open(self.get_test_loc("cpan/variable-2009110702.meta")) as cpan_metadata:
            metadata = cpan_metadata.read()
        packages = mappers.cpan.build_packages_from_metafile(
            metadata,
            "http://www.cpan.org/authors/id/A/AB/ABIGAIL/variable-2009110702.metadata",
            "pkg:cpan/variable@2009110702",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("cpan/expected_yaml_cpanmapper.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_metafile_from_json(self):
        with open(
            self.get_test_loc("cpan/Regexp-Common-2016010701.meta")
        ) as cpan_metadata:
            metadata = cpan_metadata.read()
        packages = mappers.cpan.build_packages_from_metafile(
            metadata,
            "http://www.cpan.org/authors/id/A/AB/ABIGAIL/Regexp-Common-2016010701.metadata",
            "pkg:cpan/Regexp-Common@2016010701",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("cpan/expected_json_cpanmapper.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_readme_from_json(self):
        uri = "http://www.cpan.org/authors/id/A/AM/AMIRITE/Mojolicious-Plugin-Nour-Config-0.09.readme"
        test_loc = self.get_test_loc("cpan/Mojolicious-Plugin-Nour-Config-0.09.readme")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = cpan.CpanReadmeVisitors(uri)
        packages = mappers.cpan.build_packages_from_readmefile(
            data,
            "http://www.cpan.org/authors/id/A/AM/AMIRITE/Mojolicious-Plugin-Nour-Config-0.09.readme",
            "pkg:cpan/Mojolicious-Plugin-Nour-Config@0.09",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "cpan/expected_json_readmefile_cpanmapper.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_readme_from_json2(self):
        uri = "http://www.cpan.org/authors/id/A/AB/ABIGAIL/Algorithm-Graphs-TransitiveClosure-2009110901.readme"
        test_loc = self.get_test_loc(
            "cpan/Algorithm-Graphs-TransitiveClosure-2009110901.readme",
            "pkg:cpan/Algorithm-Graphs-TransitiveClosure@2009110901",
        )
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = cpan.CpanReadmeVisitors(uri)
        packages = mappers.cpan.build_packages_from_readmefile(
            data,
            "http://www.cpan.org/authors/id/A/AB/ABIGAIL/Algorithm-Graphs-TransitiveClosure-2009110901.readme",
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "cpan/expected_json_readmefile_cpanmapper2.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)
