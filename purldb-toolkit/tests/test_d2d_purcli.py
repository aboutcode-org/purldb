from itertools import groupby
import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from purldb_toolkit.purlcli import (
    d2d,
    d2d_purl_set,
    D2DPackage,
    get_set_packages,
    get_packages_set,
    get_sets,
    PackagePair,
    PackageContentType,
    generate_d2d_package_pairs,
    get_package_pairs_for_d2d,
)

@pytest.fixture
def runner():
    return CliRunner()

@patch("purldb_toolkit.purlcli.requests.get")
def test_get_packages_set(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"packages": [{"purl": "pkg:example/1", "package_content": "source_repo", "download_url": "http://example.com/1"}]}]}
    mock_requests_get.return_value = mock_response

    result = get_packages_set("set_uuid", "https://public.purldb.io/api")
    assert result == {"results": [{"packages": [{"purl": "pkg:example/1", "package_content": "source_repo", "download_url": "http://example.com/1"}]}]}

@patch("purldb_toolkit.purlcli.get_packages_set")
def test_get_set_packages(mock_get_packages_set):
    mock_get_packages_set.return_value = {"results": [{"packages": [{"purl": "pkg:example/1", "package_content": "source_repo", "download_url": "http://example.com/1"}]}]}

    packages = list(get_set_packages("set_uuid", "https://public.purldb.io/api"))
    assert len(packages) == 1
    assert packages[0] == D2DPackage(purl="pkg:example/1", package_content="source_repo", download_url="http://example.com/1")

@patch("purldb_toolkit.purlcli.requests.get")
def test_get_sets(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"package_sets": [{"uuid": "set_uuid"}]}]}
    mock_requests_get.return_value = mock_response

    sets = list(get_sets("pkg:example/1", "https://public.purldb.io/api"))
    assert len(sets) == 1
    assert sets[0] == "set_uuid"

def test_generate_d2d_package_pairs():
    from_package = D2DPackage(purl="pkg:example/1", package_content="source_repo", download_url="http://example.com/1")
    to_package = D2DPackage(purl="pkg:example/2", package_content="binary", download_url="http://example.com/2")

    pairs = list(generate_d2d_package_pairs([from_package], [to_package]))
    assert len(pairs) == 1
    assert pairs[0] == PackagePair(from_package=from_package, to_package=to_package)


@patch("purldb_toolkit.purlcli.requests.get")
@patch("purldb_toolkit.purlcli.map_deploy_to_devel")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_project_data")
@patch("purldb_toolkit.purlcli.get_download_urls")
def test_d2d_command(mock_get_download_urls, mock_get_project_data, mock_get_run_data, mock_map_deploy_to_devel, mock_requests_get, runner):
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


@patch("purldb_toolkit.purlcli.requests.get")
@patch("purldb_toolkit.purlcli.requests.post")
@patch("purldb_toolkit.purlcli.get_sets")
@patch("purldb_toolkit.purlcli.get_set_packages")
@patch("purldb_toolkit.purlcli.get_package_pairs_for_d2d")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_download_urls")
def test_d2d_purl_set_command(
    mock_get_download_urls,
    mock_get_run_data,
    mock_get_package_pairs_for_d2d,
    mock_get_set_packages,
    mock_get_sets,
    mock_requests_post,
    mock_requests_get,
    runner
):
    # Mock return values
    mock_get_sets.return_value = ["set_uuid_1"]
    mock_get_set_packages.return_value = [
        D2DPackage(purl="pkg:example/from@1.0.0", package_content="source_repo", download_url="http://example.com/from_download"),
        D2DPackage(purl="pkg:example/to@2.0.0", package_content="binary", download_url="http://example.com/to_download")
    ]
    mock_get_package_pairs_for_d2d.return_value = [
        PackagePair(
            from_package=D2DPackage(purl="pkg:example/from@1.0.0", package_content="source_repo", download_url="http://example.com/from_download"),
            to_package=D2DPackage(purl="pkg:example/to@2.0.0", package_content="binary", download_url="http://example.com/to_download")
        )
    ]
    mock_get_download_urls.return_value = ("http://example.com/from_download", "http://example.com/to_download")
    mock_requests_post.return_value.json.return_value = {"runs": ["run_id"], "url": "http://example.com/project"}
    mock_requests_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"status": "success", "data": "test_data"})
    ]

    mock_get_run_data.side_effect = [
        {"status": "running"},
        {"status": "success", "data": "test_data"}
    ]

    # Run the CLI command
    with runner.isolated_filesystem():
        result = runner.invoke(d2d_purl_set, [
            "--purl", "pkg:example/purl_set",
            "--output", "output.json",
            "--purldb-api-url", "https://public.purldb.io/api",
            "--matchcode-api-url", "https://matchcode.io/api"
        ])

        # Assertions
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

