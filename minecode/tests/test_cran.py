#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from django.test import TestCase as DjangoTestCase
from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting

from minecode import miners
from minecode.miners.cran import get_download_url
from minecode.models import ResourceURI
from minecode.miners import cran
from minecode.tests import FIXTURES_REGEN


class CranVistorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_metacpan_api_projects(self):
        uri = 'https://cloud.r-project.org/web/packages/available_packages_by_date.html'
        test_loc = self.get_test_loc('cran/CRAN_Packages_By_Date.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = cran.CranPackagesVisitors(uri)
        expected_loc = self.get_test_loc('cran/expected_cran_pacakges.json')
        self.check_expected_uris(uris, expected_loc, regen=FIXTURES_REGEN)


class CranMapperTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages_from_directory_listing(self):
        ResourceURI.objects.create(
            uri='https://cloud.r-project.org/web/packages/ANN2/index.html')
        with open(self.get_test_loc('cran/CRAN_Package_ANN2.html')) as html_metadata:
            metadata = html_metadata.read()
        packages = miners.cran.build_packages_from_html(metadata, 'https://cloud.r-project.org/web/packages/ANN2/index.html', 'pkg:cran/ANN2')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('cran/mapper_ANN2_expected.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)

    def test_build_packages_from_directory_listing2(self):
        ResourceURI.objects.create(
            uri='https://cloud.r-project.org/web/packages/abe/index.html')
        with open(self.get_test_loc('cran/CRAN_Package_abe.html')) as html_metadata:
            metadata = html_metadata.read()
        packages = miners.cran.build_packages_from_html(metadata, 'https://cloud.r-project.org/web/packages/abe/index.htm', 'pkg:cran/abe')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('cran/mapper_abe_expected.json')
        self.check_expected_results(
            packages, expected_loc, regen=FIXTURES_REGEN)

    def test_replace_downloadurl(self):
        url = "../../../src/contrib/Archive/ANN2"
        result = get_download_url(url)
        expected_url = 'https://cloud.r-project.org/src/contrib/Archive/ANN2'
        self.assertEqual(expected_url, result)
