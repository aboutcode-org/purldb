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

import minecode.collectors.hex as hex_collector
import minecode.miners.hex as hex_miner


@pytest.fixture
def package_url():
    return PackageURL.from_string("pkg:hex/phoenix@1.7.11")


def test_get_hex_package_json_success():
    with patch("minecode.collectors.hex.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"name": "phoenix"}
        mock_get.return_value = mock_response

        result = hex_collector.get_hex_package_json("phoenix")
        assert result == {"name": "phoenix"}
        mock_get.assert_called_once_with("https://hex.pm/api/packages/phoenix")


def test_get_hex_package_json_http_error():
    with patch("minecode.collectors.hex.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = hex_collector.get_hex_package_json("badpkg")
        assert result is None


def test_map_hex_package_success(package_url):
    with (
        patch("minecode.collectors.hex.get_hex_package_json") as mock_get_json,
        patch("minecode.collectors.hex.build_packages") as mock_build,
        patch("minecode.model_utils.merge_or_create_package") as mock_merge,
        patch("minecode.model_utils.add_package_to_scan_queue") as mock_add,
    ):
        mock_get_json.return_value = {"meta": {}, "releases": []}
        mock_package = MagicMock()
        mock_build.return_value = [mock_package]
        mock_merge.return_value = ("db_package", None, None, None)

        error = hex_collector.map_hex_package(package_url, pipelines=["p1"], priority=2)

        assert error is None
        mock_get_json.assert_called_once()
        mock_build.assert_called_once()
        mock_merge.assert_called_once()
        mock_add.assert_called_once_with(package="db_package", pipelines=["p1"], priority=2)


def test_map_hex_package_not_found(package_url):
    with patch("minecode.collectors.hex.get_hex_package_json") as mock_get_json:
        mock_get_json.return_value = None

        error = hex_collector.map_hex_package(package_url, pipelines=[])
        assert "Package does not exist" in error


def test_build_single_package_creates_package():
    version_info = {
        "html_url": "https://hex.pm/packages/phoenix/1.7.11",
        "checksum": "deadbeef",
    }
    metadata_dict = {
        "meta": {"description": "test desc", "licenses": ["MIT"]},
        "owners": [{"username": "joe", "email": "joe@example.com"}],
        "inserted_at": "2024-01-01T00:00:00Z",
    }

    pkg = hex_miner.build_single_package(
        version_info=version_info,
        package_name="phoenix",
        version="1.7.11",
        metadata_dict=metadata_dict,
    )

    assert pkg.name == "phoenix"
    assert pkg.version == "1.7.11"
    assert pkg.description == "test desc"
    assert pkg.license_detections == ["MIT"]
    assert pkg.parties[0].name == "joe"
    assert pkg.sha256 == "deadbeef"


def test_build_packages_with_version(package_url):
    with (
        patch("minecode.miners.hex.requests.get") as mock_get,
        patch("minecode.miners.hex.build_single_package") as mock_build,
    ):
        mock_get.return_value.json.return_value = {"html_url": "fake"}
        mock_build.return_value = "fake_package"

        results = list(hex_miner.build_packages({"meta": {}}, package_url))
        assert results == ["fake_package"]
        mock_get.assert_called_once()


def test_build_packages_all_versions():
    purl = PackageURL(type="hex", name="phoenix")
    metadata = {
        "releases": [
            {"version": "1.0.0", "url": "https://hex.pm/api/packages/phoenix/releases/1.0.0"}
        ]
    }

    with (
        patch("minecode.miners.hex.requests.get") as mock_get,
        patch("minecode.miners.hex.build_single_package") as mock_build,
    ):
        mock_get.return_value.json.return_value = {"html_url": "fake"}
        mock_build.return_value = "fake_package"

        results = list(hex_miner.build_packages(metadata, purl))
        assert results == ["fake_package"]
        mock_get.assert_called_once()
