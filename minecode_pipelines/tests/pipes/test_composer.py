#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase

from minecode_pipelines.miners.composer import get_composer_packages
from minecode_pipelines.miners.composer import load_composer_packages
from minecode_pipelines.miners.composer import get_composer_purl

DATA_DIR = Path(__file__).parent.parent / "test_data" / "composer"


class ComposerPipelineTests(SimpleTestCase):
    @patch("requests.get")
    def test_generate_purls_from_composer(self, mock_get):
        """
        Test mining composer packages and generating PURLs with mocked Packagist requests
        using JSON files stored in test_data/composer.
        """

        with open(DATA_DIR / "packages_list.json", encoding="utf-8") as f:
            fake_packages_list = json.load(f)

        with open(DATA_DIR / "package_details.json", encoding="utf-8") as f:
            fake_package_details = json.load(f)

        with open(DATA_DIR / "expected_output.json", encoding="utf-8") as f:
            expected_output = json.load(f)

        resp_list = MagicMock()
        resp_list.ok = True
        resp_list.json.return_value = fake_packages_list

        resp_package_details = MagicMock()
        resp_package_details.ok = True
        resp_package_details.json.return_value = fake_package_details

        mock_get.side_effect = [resp_list, resp_package_details]

        packages_file = get_composer_packages()
        packages = load_composer_packages(packages_file)

        all_purls = []
        for vendor, package in packages:
            purls = get_composer_purl(vendor, package)
            all_purls.extend(purls)

        assert len(all_purls) == 85
        assert all_purls == expected_output
