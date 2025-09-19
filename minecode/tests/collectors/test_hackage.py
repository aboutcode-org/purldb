#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import pytest
from unittest.mock import patch

from packageurl import PackageURL
import requests

import minecode.collectors.hackage as hackage


@pytest.fixture
def package_url():
    return PackageURL.from_string("pkg:hackage/ac-halfinteger@1.1.1")


def test_map_hackage_package_success(package_url):
    with (
        patch("minecode.collectors.hackage.get_hackage_package_json") as mock_get_json,
        patch("minecode.model_utils.merge_or_create_package") as mock_merge,
        patch("minecode.model_utils.add_package_to_scan_queue") as mock_add,
    ):
        mock_get_json.return_value = {"1.1.1": "normal", "1.2.1": "normal"}
        mock_merge.return_value = ("db_package", None, None, None)

        error = hackage.map_hackage_package(package_url, pipelines=["p1"], priority=1)

        assert error is None
        mock_get_json.assert_called_once_with(name="ac-halfinteger")
        mock_merge.assert_called_once()
        mock_add.assert_called_once_with(package="db_package", pipelines=["p1"], priority=1)


def test_map_hackage_package_version_not_found(package_url):
    with patch("minecode.collectors.hackage.get_hackage_package_json") as mock_get_json:
        mock_get_json.return_value = {"2.0.0": "normal"}

        error = hackage.map_hackage_package(package_url, pipelines=[])
        assert "not found" in error


def test_map_hackage_package_network_error(package_url):
    with patch("minecode.collectors.hackage.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Network down")

        data = hackage.get_hackage_package_json(package_url.name)
        assert data is None
