# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import json
import os
import re

from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode.miners.bitbucket import build_bitbucket_download_packages
from minecode.miners.bitbucket import build_bitbucket_repo_package

from minecode.miners.bitbucket import BitbucketDetailsVisitorPaginated
from minecode.miners.bitbucket import BitbucketIndexVisitor
from minecode.miners.bitbucket import BitbucketSingleRepoVisitor

from minecode.tests import FIXTURES_REGEN


class BitbucketVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles')

    def test_BitbucketIndexVisitor(self):
        uri = 'https://api.bitbucket.org/2.0/repositories?pagelen=10'
        test_loc = self.get_test_loc('bitbucket/visit/index-repositories.json')

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = BitbucketIndexVisitor(uri)

        expected_uri_loc = self.get_test_loc(
            'bitbucket/visit/index-repositories_expected_uris.json')
        self.check_expected_uris(uris, expected_uri_loc, regen=FIXTURES_REGEN)

        expected_data_loc = self.get_test_loc(
            'bitbucket/visit/index-repositories_expected_data.json')
        self.check_expected_results(
            data, expected_data_loc, regen=FIXTURES_REGEN)

    def test_BitbucketSingleRepoVisitor(self):
        uri = 'https://api.bitbucket.org/2.0/repositories/bastiand/mercurialeclipse/'
        test_loc = self.get_test_loc('bitbucket/visit/singlerepo.json')

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = BitbucketSingleRepoVisitor(uri)

        expected_data_loc = self.get_test_loc(
            'bitbucket/visit/singlerepo_expected_data.json')
        self.check_expected_results(
            data, expected_data_loc, regen=FIXTURES_REGEN)

        expected_uris_loc = self.get_test_loc(
            'bitbucket/visit/singlerepo_expected_uris.json')
        self.check_expected_uris(uris, expected_uris_loc, regen=FIXTURES_REGEN)

    def test_BitbucketDetailsVisitorPaginated(self):
        uri = 'https://api.bitbucket.org/2.0/repositories/bastiand/mercurialeclipse/refs/tags?pagelen=2'
        test_loc = self.get_test_loc('bitbucket/visit/paginated_tags.json')

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = BitbucketDetailsVisitorPaginated(uri)

        expected_data_loc = self.get_test_loc(
            'bitbucket/visit/paginated_tags_expected_data.json')
        self.check_expected_results(
            data, expected_data_loc, regen=FIXTURES_REGEN)

        expected_uris_loc = self.get_test_loc(
            'bitbucket/visit/paginated_tags_expected_uris.json')
        self.check_expected_uris(uris, expected_uris_loc, regen=FIXTURES_REGEN)


class BitbucketMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testfiles')

    def test_pattern_match_without_download(self):
        url = 'https://api.bitbucket.org/2.0/repositories/phlogistonjohn/tweakmsg'
        pattern = 'https://api.bitbucket.org/2.0/repositories/.*(?<!downloads)/?\Z'
        result = re.search(pattern, url)
        self.assertTrue(result)

    def test_pattern_match_with_download_with_slash(self):
        url = 'https://api.bitbucket.org/2.0/repositories/bastiand/mercurialeclipse/downloads/'
        pattern = 'https://api.bitbucket.org/2.0/repositories/.*/downloads/'
        result = re.search(pattern, url)
        self.assertTrue(result)

    def test_pattern_match_with_download_without_slash(self):
        url = 'https://api.bitbucket.org/2.0/repositories/bastiand/mercurialeclipse/downloads'
        pattern = 'https://api.bitbucket.org/2.0/repositories/.*/downloads/?'
        result = re.search(pattern, url)
        self.assertTrue(result)

    def test_build_bitbucket_repo_package(self):
        with open(self.get_test_loc('bitbucket/map/repository.json')) as pck:
            repo_data = json.load(pck, object_pairs_hook=OrderedDict)
        purl = 'pkg:bitbucket/bastiand/mercurialeclipse'
        package = build_bitbucket_repo_package(repo_data, purl)
        expected_loc = self.get_test_loc(
            'bitbucket/map/repository_expected.json')
        self.check_expected_results(
            package.to_dict(), expected_loc, regen=FIXTURES_REGEN)

    def test_build_bitbucket_repo_package_with_issues(self):
        with open(self.get_test_loc('bitbucket/map/tweakmsg.json')) as pck:
            repo_data = json.load(pck, object_pairs_hook=OrderedDict)
        purl = 'pkg:bitbucket/phlogistonjohn/tweakmsg'
        package = build_bitbucket_repo_package(repo_data, purl)
        expected_loc = self.get_test_loc(
            'bitbucket/map/tweakmsg_expected.json')
        self.check_expected_results(
            package.to_dict(), expected_loc, regen=FIXTURES_REGEN)

    def test_build_bitbucket_download_packages_single(self):
        with open(self.get_test_loc('bitbucket/map/downloads.json')) as pck:
            dnl_data = json.load(pck, object_pairs_hook=OrderedDict)
        purl = 'pkg:bitbucket/bastiand/mercurialeclipse'
        packages = build_bitbucket_download_packages(dnl_data, purl)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'bitbucket/map/downloads_expected.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_bitbucket_download_packages_many(self):
        with open(self.get_test_loc('bitbucket/map/downloads_many.json')) as pck:
            dnl_data = json.load(pck, object_pairs_hook=OrderedDict)
        purl = 'pkg:bitbucket/pypa/setuptools'
        packages = build_bitbucket_download_packages(dnl_data, purl)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            'bitbucket/map/downloads_many_expected.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)
