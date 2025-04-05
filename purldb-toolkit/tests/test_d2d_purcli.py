import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch
from unittest.mock import MagicMock

from purldb_toolkit.purlcli import d2d
from purldb_toolkit.purlcli import D2DPackage
from purldb_toolkit.purlcli import PackagePair
from purldb_toolkit.purlcli import generate_d2d_package_pairs
from purldb_toolkit.purlcli import get_run_data
from purldb_toolkit.purlcli import get_project_results
from purldb_toolkit.purlcli import get_download_url
from purldb_toolkit.purlcli import get_package

from purldb_toolkit import purlcli

purlcli.POLLING_INTERVAL = 0.01


@pytest.fixture
def runner():
    return CliRunner()


def test_generate_d2d_package_pairs():
    from_package = D2DPackage(
        purl="pkg:example/1", package_content="source_repo", download_url="http://example.com/1"
    )
    to_package = D2DPackage(
        purl="pkg:example/2", package_content="binary", download_url="http://example.com/2"
    )

    pairs = list(generate_d2d_package_pairs([from_package], [to_package]))
    assert len(pairs) == 1
    assert pairs[0] == PackagePair(from_package=from_package, to_package=to_package)


@patch("purldb_toolkit.purlcli.get_package_pairs_for_d2d")
@patch("purldb_toolkit.purlcli.map_deploy_to_devel")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_project_results")
@patch("purldb_toolkit.purlcli.get_packages_by_set")
def test_d2d_purl_set_command(
    mock_get_packages_by_set,
    mock_get_project_results,
    mock_get_run_data,
    mock_map_deploy_to_devel,
    mock_get_package_pairs_for_d2d,
    runner,
):
    from_pkg = D2DPackage(
        purl="pkg:example/from@1.0.0",
        package_content="source_repo",
        download_url="http://example.com/from_download",
    )
    to_pkg = D2DPackage(
        purl="pkg:example/to@2.0.0",
        package_content="binary",
        download_url="http://example.com/to_download",
    )

    mock_get_packages_by_set.return_value = [[from_pkg, to_pkg]]
    mock_get_package_pairs_for_d2d.return_value = [
        PackagePair(from_package=from_pkg, to_package=to_pkg)
    ]

    mock_map_deploy_to_devel.return_value = ("run_id", "http://example.com/project")
    mock_get_run_data.side_effect = [
        {"status": "running"},
        {"status": "success", "data": "test_data"},
    ]
    mock_get_project_results.return_value = {"status": "success", "data": "test_data"}

    with runner.isolated_filesystem():
        result = runner.invoke(
            d2d,
            [
                "--purl",
                "pkg:example/purl_set",
                "--output",
                "output.json",
                "--purldb-api-url",
                "https://public.purldb.io/api",
                "--matchcode-api-url",
                "https://matchcode.io/api",
            ],
        )

        if result.exit_code != 0:
            raise Exception(result.output)

        with open("output.json") as f:
            data = json.load(f)
            assert data == [
                {
                    "results": {
                        "from": {
                            "purl": "pkg:example/from@1.0.0",
                            "package_content": "source_repo",
                            "download_url": "http://example.com/from_download",
                        },
                        "to": {
                            "purl": "pkg:example/to@2.0.0",
                            "package_content": "binary",
                            "download_url": "http://example.com/to_download",
                        },
                        "d2d_result": {"status": "success", "data": "test_data"},
                    }
                }
            ]


@patch("purldb_toolkit.purlcli.requests.get")
def test_get_package(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"download_url": "http://example.com/1"}]}
    mock_requests_get.return_value = mock_response

    result = get_package("pkg:example/1", "https://public.purldb.io/api")
    assert result == {"results": [{"download_url": "http://example.com/1"}]}


@patch("purldb_toolkit.purlcli.requests.get")
def test_get_download_url(mock_requests_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"download_url": "http://example.com/1"}]}
    mock_requests_get.return_value = mock_response

    from_url = get_download_url("pkg:example/from@1.0.0", "https://public.purldb.io/api")
    assert from_url == "http://example.com/1"


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

    result = get_project_results("http://example.com/project")
    assert result == {"status": "success", "data": "test_data"}


@patch("purldb_toolkit.purlcli.map_deploy_to_devel")
@patch("purldb_toolkit.purlcli.get_run_data")
@patch("purldb_toolkit.purlcli.get_project_results")
@patch("purldb_toolkit.purlcli.get_download_url")
@patch("purldb_toolkit.purlcli.get_download_url")
def test_d2d_command(
    mock_get_download_url_to,
    mock_get_download_url_from,
    mock_get_project_results,
    mock_get_run_data,
    mock_map_deploy_to_devel,
    runner,
):
    mock_get_download_url_to.return_value = "http://example.com/to_download"
    mock_get_download_url_from.return_value = "http://example.com/from_download"

    mock_map_deploy_to_devel.return_value = ("run_id", "http://example.com/project")
    mock_get_run_data.side_effect = [
        {"status": "running"},
        {"status": "running"},
        {"status": "success", "data": "test_data"},
    ]
    mock_get_project_results.return_value = {"status": "success", "data": "test_data"}

    with runner.isolated_filesystem():
        result = runner.invoke(
            d2d,
            [
                "--purl",
                "pkg:example/from@1.0.0",
                "--purl",
                "pkg:example/to@2.0.0",
                "--output",
                "output.json",
                "--purldb-api-url",
                "https://public.purldb.io/api",
                "--matchcode-api-url",
                "https://matchcode.io/api",
            ],
        )

        if result.exit_code != 0:
            raise Exception(result.output)

        with open("output.json") as f:
            data = json.load(f)
            assert data == {"status": "success", "data": "test_data"}
