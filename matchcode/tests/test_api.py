#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.urls import reverse

from packagedb.models import Package

from matchcode.utils import index_package_directories
from matchcode.utils import load_resources_from_scan
from matchcode.utils import MatchcodeTestCase
from matchcode.tests import FIXTURES_REGEN


class ApproximateDirectoryStructureIndexAPITestCase(MatchcodeTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        # Execute the superclass' setUp method before creating our own
        # DB objects
        super().setUp()

        self.test_package1, _ = Package.objects.get_or_create(
            filename='plugin-request-2.4.1.tgz',
            sha1='7295749caddd3c52be472eef6623a7b441ed17d6',
            size=7269,
            name='plugin-request',
            version='2.4.1',
            download_url='https://registry.npmjs.org/@umijs/plugin-request/-/plugin-request-2.4.1.tgz',
            type='npm',
        )
        load_resources_from_scan(self.get_test_loc('match/nested/plugin-request-2.4.1-ip.json'), self.test_package1)
        index_package_directories(self.test_package1)

        self.test_package2, _ = Package.objects.get_or_create(
            filename='underscore-1.10.9.tgz',
            sha1='ba7a9cfc15873e67821611503a34a7c26bf7264f',
            size=26569,
            name='underscore',
            version='1.10.9',
            download_url='https://registry.npmjs.org/@types/underscore/-/underscore-1.10.9.tgz',
            type='npm',
        )
        load_resources_from_scan(self.get_test_loc('match/nested/underscore-1.10.9-ip.json'), self.test_package2)
        index_package_directories(self.test_package2)

    def test_api_approximate_directory_content_index_list_fingerprint_lookup(self):
        test_fingerprint = '00000007af7d63765c78fa516b5353f5ffa7df45'
        response = self.client.get(
            reverse('api:approximatedirectorycontentindex-list'),
            data={'fingerprint': test_fingerprint}
        )
        self.assertEqual(200, response.status_code)
        results = response.data.get('results', [])
        self.assertEqual(1, len(results))
        result = results[0]
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package1.uuid])
        expected_result = {
            'fingerprint': '00000007af7d63765c78fa516b5353f5ffa7df45',
            'package': expected_package
        }
        self.assertEqual(expected_result, result)

    def test_api_approximate_directory_structure_index_list_fingerprint_lookup(self):
        test_fingerprint = '00000004d10982208810240820080a6a3e852486'
        response = self.client.get(
            reverse('api:approximatedirectorystructureindex-list'),
            data={'fingerprint': test_fingerprint}
        )
        self.assertEqual(200, response.status_code)
        results = response.data.get('results', [])
        self.assertEqual(1, len(results))
        result = results[0]
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package2.uuid])
        expected_result = {
            'fingerprint': '00000004d10982208810240820080a6a3e852486',
            'package': expected_package
        }
        self.assertEqual(expected_result, result)

    def test_api_approximate_directory_content_index_match_no_match(self):
        test_fingerprint = '000000020e1d2124040134564e1941a6a620db34'
        response = self.client.get(
            reverse('api:approximatedirectorycontentindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(0, len(results))

    def test_api_approximate_directory_structure_index_match_no_match(self):
        test_fingerprint = '00000004d10982789010240876580a6a3e852485'
        response = self.client.get(
            reverse('api:approximatedirectorystructureindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(0, len(results))

    def test_api_approximate_directory_content_index_match_close_match(self):
        # This test fingerprint has a hamming distance of 7 from the expected fingerprint
        test_fingerprint = '00000007af7d63765c78fa516b5353f5ffa7d000'
        response = self.client.get(
            reverse('api:approximatedirectorycontentindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(test_fingerprint, result['fingerprint'])
        expected_matched_fingerprint = '00000007af7d63765c78fa516b5353f5ffa7df45'
        self.assertEqual(expected_matched_fingerprint, result['matched_fingerprint'])
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package1.uuid])
        self.assertEqual(expected_package, result['package'])
        self.assertEqual(0.9453125, result['similarity_score'])

    def test_api_approximate_directory_structure_index_match_close_match(self):
        # This test fingerprint has a hamming distance of 7 from the expected fingerprint
        test_fingerprint = '00000004d10982208810240820080a6a3e800000'
        response = self.client.get(
            reverse('api:approximatedirectorystructureindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(test_fingerprint, result['fingerprint'])
        expected_matched_fingerprint = '00000004d10982208810240820080a6a3e852486'
        self.assertEqual(expected_matched_fingerprint, result['matched_fingerprint'])
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package2.uuid])
        self.assertEqual(expected_package, result['package'])
        self.assertEqual(0.9453125, result['similarity_score'])

    def test_api_approximate_directory_content_index_match(self):
        test_fingerprint = '00000007af7d63765c78fa516b5353f5ffa7df45'
        response = self.client.get(
            reverse('api:approximatedirectorycontentindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(test_fingerprint, result['fingerprint'])
        self.assertEqual(test_fingerprint, result['matched_fingerprint'])
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package1.uuid])
        self.assertEqual(expected_package, result['package'])
        self.assertEqual(1.0, result['similarity_score'])

    def test_api_approximate_directory_structure_index_match(self):
        test_fingerprint = '00000004d10982208810240820080a6a3e852486'
        response = self.client.get(
            reverse('api:approximatedirectorystructureindex-match'),
            data={'fingerprint': test_fingerprint}
        )
        results = response.data
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(test_fingerprint, result['fingerprint'])
        self.assertEqual(test_fingerprint, result['matched_fingerprint'])
        expected_package = 'http://testserver' + reverse('api:package-detail', args=[self.test_package2.uuid])
        self.assertEqual(expected_package, result['package'])
        self.assertEqual(1.0, result['similarity_score'])
