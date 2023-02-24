#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os
from collections import OrderedDict


from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.visitors import dockerhub
from minecode import mappers


class DockerHubTest(JsonBasedTesting):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')


class DockerHubVistorTest(DockerHubTest):

    def test_searching_condition(self):
        combinations = dockerhub.get_search_conditions()
        expected_file = self.get_test_loc('dockerhub/conditions_expected')
        self.check_expected_results(combinations, expected_file, regen=False)

    def test_seeds(self):
        seed = dockerhub.DockerHubSeed()
        seeds = list(seed.get_seeds())
        expected_file = self.get_test_loc('dockerhub/seeds_expected')
        self.check_expected_results(seeds, expected_file, regen=False)

    def test_visit_dockerhub_exlpore_page(self):
        uri = 'https://hub.docker.com/explore/?page=1'
        test_loc = self.get_test_loc('dockerhub/Explore_DockerHub_Page1.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = dockerhub.DockHubExplorePageVisitor(uri)
        expected_loc = self.get_test_loc(
            'dockerhub/visitor_explore_page1_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)

    def test_visit_dockerhub_project(self):
        uri = 'https://hub.docker.com/_/elixir/'
        test_loc = self.get_test_loc('dockerhub/library_elixir.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = dockerhub.DockHubProjectHTMLVisitor(uri)

        result = json.loads(data, object_pairs_hook=OrderedDict)
        expected_file = self.get_test_loc(
            'dockerhub/visitor_library_elixir_expected')
        self.check_expected_results(result, expected_file, regen=False)

    def test_visit_dockerhub_search_api(self):
        uri = 'https://index.docker.io/v1/search?q=1a&n=100&page=2'
        test_loc = self.get_test_loc('dockerhub/search.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = dockerhub.DockHubLibraryRESTJsonVisitor(uri)
        expected_loc = self.get_test_loc('dockerhub/visitor_search_expected')
        self.check_expected_uris(uris, expected_loc, regen=False)


class DockerHubMapperTest(DockerHubTest):

    def test_build_packages_fromjson(self):
        with open(self.get_test_loc('dockerhub/elixir.json')) as dockerhub_metadata:
            metadata = dockerhub_metadata.read()
        packages = mappers.dockerhub.build_packages_from_jsonfile(
            metadata, 'https://registry.hub.docker.com/v2/repositories/library')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'dockerhub/expected_dockerhubmapper.json')
        self.check_expected_results(packages, expected_loc, regen=False)
