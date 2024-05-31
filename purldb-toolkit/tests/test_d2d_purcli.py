from itertools import groupby
import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from purldb_toolkit.purlcli import (
    d2d,
    d2d_purl_set,
    D2DPackage,
    get_packages_by_set,
    PackagePair,
    PackageContentType,
    generate_d2d_package_pairs,
    get_package_pairs_for_d2d,
    map_deploy_to_devel,
    get_run_data,
    get_project_data,
    get_download_urls,
    get_package,
)


@pytest.fixture
def runner():
    return CliRunner()

def test_generate_d2d_package_pairs():
    from_package = D2DPackage(purl="pkg:example/1", package_content="source_repo", download_url="http://example.com/1")
    to_package = D2DPackage(purl="pkg:example/2", package_content="binary", download_url="http://example.com/2")

    pairs = list(generate_d2d_package_pairs([from_package], [to_package]))
    assert len(pairs) == 1
    assert pairs[0] == PackagePair(from_package=from_package, to_package=to_package)


@patch("purldb_toolkit.purlcli.get_package_pairs_for_d2d")
@patch("purldb_toolkit.purlcli.map_deploy_to_devel")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_project_data")
@patch("purldb_toolkit.purlcli.get_packages_by_set")
def test_d2d_purl_set_command(mock_get_packages_by_set, mock_get_project_data, mock_get_run_data, mock_map_deploy_to_devel, mock_get_package_pairs_for_d2d, runner):
    mock_get_packages_by_set.return_value = [
        [
            D2DPackage(purl="pkg:example/from@1.0.0", package_content="source_repo", download_url="http://example.com/from_download"),
            D2DPackage(purl="pkg:example/to@2.0.0", package_content="binary", download_url="http://example.com/to_download")
        ]
    ]
    mock_get_package_pairs_for_d2d.return_value = [
        PackagePair(
            from_package=D2DPackage(purl="pkg:example/from@1.0.0", package_content="source_repo", download_url="http://example.com/from_download"),
            to_package=D2DPackage(purl="pkg:example/to@2.0.0", package_content="binary", download_url="http://example.com/to_download")
        )
    ]
    mock_map_deploy_to_devel.return_value = ("run_id", "http://example.com/project")
    mock_get_run_data.side_effect = [
        {"status": "running"},
        {"status": "success", "data": "test_data"}
    ]
    mock_get_project_data.return_value = {"status": "success", "data": "test_data"}

    with runner.isolated_filesystem():
        result = runner.invoke(d2d_purl_set, [
            "--purl", "pkg:example/purl_set",
            "--output", "output.json",
            "--purldb-api-url", "https://public.purldb.io/api",
            "--matchcode-api-url", "https://matchcode.io/api"
        ])

        if result.exit_code != 0:
            print(result.output)

        assert result.exit_code == 0
        with open("output.json") as f:
            data = json.load(f)
            assert data == [{
                "results": {
                    "from": {
                        "purl": "pkg:example/from@1.0.0",
                        "package_content": "source_repo",
                        "download_url": "http://example.com/from_download"
                    },
                    "to": {
                        "purl": "pkg:example/to@2.0.0",
                        "package_content": "binary",
                        "download_url": "http://example.com/to_download"
                    },
                    "d2d_result": {"status": "success", "data": "test_data"}
                }
            }]



@patch("purldb_toolkit.purlcli.requests.get")
def test_get_package(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"download_url": "http://example.com/1"}]}
    mock_requests_get.return_value = mock_response

    result = get_package("pkg:example/1", "https://public.purldb.io/api")
    assert result == {"results": [{"download_url": "http://example.com/1"}]}


@patch("purldb_toolkit.purlcli.requests.get")
def test_get_download_urls(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"download_url": "http://example.com/1"}]}
    mock_requests_get.return_value = mock_response

    from_url, to_url = get_download_urls("pkg:example/from@1.0.0", "pkg:example/to@2.0.0", "https://public.purldb.io/api")
    assert from_url == "http://example.com/1"
    assert to_url == "http://example.com/1"


@patch("purldb_toolkit.purlcli.requests.get")
def test_get_run_data(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "running"}
    mock_requests_get.return_value = mock_response

    result = get_run_data("https://matchcode.io/api", "run_id")
    assert result == {"status": "running"}


@patch("purldb_toolkit.purlcli.requests.get")
def test_get_project_data(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success", "data": "test_data"}
    mock_requests_get.return_value = mock_response

    result = get_project_data("http://example.com/project")
    assert result == {"status": "success", "data": "test_data"}


@patch("purldb_toolkit.purlcli.map_deploy_to_devel")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_project_data")
@patch("purldb_toolkit.purlcli.get_download_urls")
def test_d2d_command(mock_get_download_urls, mock_get_project_data, mock_get_run_data, mock_map_deploy_to_devel, runner):
    mock_get_download_urls.return_value = ("http://example.com/from_download", "http://example.com/to_download")
    mock_map_deploy_to_devel.return_value = ("run_id", "http://example.com/project")
    mock_get_run_data.side_effect = [
        {"status": "running"},
        {"status": "running"},
        {"status": "success", "data": "test_data"}
    ]
    mock_get_project_data.return_value = {"status": "success", "data": "test_data"}

    with runner.isolated_filesystem():
        result = runner.invoke(d2d, [
            "--from-purl", "pkg:example/from@1.0.0",
            "--to-purl", "pkg:example/to@2.0.0",
            "--output", "output.json",
            "--purldb-api-url", "https://public.purldb.io/api",
            "--matchcode-api-url", "https://matchcode.io/api/d2d"
        ])

        assert result.exit_code == 0
        with open("output.json") as f:
            data = json.load(f)
            assert data == {"status": "success", "data": "test_data"}
