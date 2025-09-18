#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import pytest
from unittest.mock import patch, MagicMock

from packageurl import PackageURL
import requests

import minecode.collectors.luarocks as luarocks


@pytest.fixture
def package_url():
    return PackageURL.from_string("pkg:luarocks/luasocket@3.1.0-1")


def test_map_lua_package_success(package_url):
    with (
        patch("minecode.collectors.luarocks.requests.head") as mock_head,
        patch("minecode.model_utils.merge_or_create_package") as mock_merge,
        patch("minecode.model_utils.add_package_to_scan_queue") as mock_add,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        mock_merge.return_value = ("db_package", None, None, None)

        error = luarocks.map_lua_package(package_url, pipelines=["p1"], priority=1)

        assert error is None
        mock_head.assert_called_once()
        mock_merge.assert_called_once()
        mock_add.assert_called_once_with(package="db_package", pipelines=["p1"], priority=1)


def test_map_lua_package_not_found(package_url):
    with patch("minecode.collectors.luarocks.requests.head") as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        error = luarocks.map_lua_package(package_url, pipelines=[])
        assert "Package does not exist" in error


def test_map_lua_package_network_error(package_url):
    with patch("minecode.collectors.luarocks.requests.head") as mock_head:
        mock_head.side_effect = requests.RequestException("Network down")

        error = luarocks.map_lua_package(package_url, pipelines=[])
        assert "Error checking package existence" in error
