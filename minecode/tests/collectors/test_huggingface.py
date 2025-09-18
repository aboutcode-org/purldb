#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
#

import pytest
from unittest.mock import patch, MagicMock

from packageurl import PackageURL
import requests

import minecode.collectors.huggingface as huggingface


@pytest.fixture
def package_url():
    return PackageURL.from_string(
        "pkg:huggingface/distilbert/distilbert-base-uncased@043235d6088ecd3dd5fb5ca3592b6913fd516027"
    )


def test_map_huggingface_package_success(package_url):
    with (
        patch("minecode.collectors.huggingface.get_hf_model_api") as mock_api,
        patch("minecode.collectors.huggingface.requests.head") as mock_head,
        patch("minecode.collectors.huggingface.fetch_license_text") as mock_license,
        patch("minecode.model_utils.merge_or_create_package") as mock_merge,
        patch("minecode.model_utils.add_package_to_scan_queue") as mock_add,
    ):
        mock_api.return_value = {
            "createdAt": "2020-01-01T00:00:00",
            "author": "HF Author",
            "siblings": [{"rfilename": "pytorch_model.bin"}],
        }

        mock_head.return_value = MagicMock(status_code=200)

        mock_license.return_value = "Apache-2.0"
        mock_merge.return_value = ("db_package", None, None, None)

        error = huggingface.map_huggingface_package(package_url, pipelines=["p1"], priority=1)

        assert error is None
        mock_api.assert_called_once()
        mock_head.assert_called()
        mock_license.assert_called_once()
        mock_merge.assert_called_once()
        mock_add.assert_called_once_with(package="db_package", pipelines=["p1"], priority=1)


def test_map_huggingface_package_missing_namespace():
    url = PackageURL.from_string("pkg:huggingface/distilbert-base-uncased@sha1")
    error = huggingface.map_huggingface_package(url, pipelines=[])
    assert "must include a namespace" in error


def test_map_huggingface_package_missing_version():
    url = PackageURL.from_string("pkg:huggingface/distilbert/distilbert-base-uncased")
    error = huggingface.map_huggingface_package(url, pipelines=[])
    assert "must include a version" in error


def test_map_huggingface_package_metadata_error(package_url):
    with patch("minecode.collectors.huggingface.get_hf_model_api") as mock_api:
        mock_api.return_value = None
        error = huggingface.map_huggingface_package(package_url, pipelines=[])
        assert "Unable to fetch model metadata" in error


def test_map_huggingface_package_head_request_failure(package_url):
    with (
        patch("minecode.collectors.huggingface.get_hf_model_api") as mock_api,
        patch("minecode.collectors.huggingface.requests.head") as mock_head,
    ):
        mock_api.return_value = {
            "createdAt": "2020-01-01T00:00:00",
            "author": "HF Author",
            "siblings": [{"rfilename": "pytorch_model.bin"}],
        }
        mock_head.side_effect = requests.RequestException("Network down")

        error = huggingface.map_huggingface_package(package_url, pipelines=[])
        assert "Error fetching model file" in error


def test_fetch_license_text_success():
    with patch("minecode.collectors.huggingface.requests.get") as mock_get:
        mock_resp = MagicMock(status_code=200, text="MIT")
        mock_get.return_value = mock_resp
        text = huggingface.fetch_license_text("http://fake-license-url")
        assert text == "MIT"


def test_fetch_license_text_not_found():
    with patch("minecode.collectors.huggingface.requests.get") as mock_get:
        mock_resp = MagicMock(status_code=404, text="Not Found")
        mock_get.return_value = mock_resp
        text = huggingface.fetch_license_text("http://fake-license-url")
        assert text is None


def test_find_siblings_with_bin_variants():
    siblings = [
        {"rfilename": "config.json"},
        {"rfilename": "pytorch_model.bin"},
        {"rfilename": "model.safetensors"},
    ]
    results = list(huggingface.find_siblings_with_bin(siblings))
    assert "pytorch_model.bin" in results
    assert any(r.endswith((".bin", ".safetensors", ".pt")) for r in results)
