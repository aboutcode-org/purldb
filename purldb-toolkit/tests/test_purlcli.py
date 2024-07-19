#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os
from collections import OrderedDict
from unittest import mock

import pytest
import requests
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting
from purldb_toolkit import cli_test_utils
from purldb_toolkit import purlcli

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


class TestPURLCLI_metadata(object):

    def test_metadata_cli_duplicate_input_sources(self):
        """
        Test the `metadata` command with both `--purl` and `--file` inputs.
        """
        options = [
            "--purl",
            "pkg:pypi/minecode",
            "--file",
            test_env.get_test_loc("purlcli/metadata_input_purls.txt"),
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_metadata, options, catch_exceptions=False)
        assert "Use either purls or file but not both." in result.output
        assert result.exit_code == 2

    def test_metadata_cli_no_input_sources(self):
        """
        Test the `metadata` command with neither `--purl` nor `--file` inputs.
        """
        options = [
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_metadata, options, catch_exceptions=False)
        assert "Error: Use either purls" in result.output
        assert result.exit_code == 2

    @mock.patch("purldb_toolkit.purlcli.collect_metadata")
    def test_metadata_details(self, mock_collect_metadata):
        mock_collect_metadata.return_value = [
            OrderedDict(
                [
                    ("purl", "pkg:pypi/fetchcode@0.1.0"),
                    ("type", "pypi"),
                    ("namespace", None),
                    ("name", "fetchcode"),
                    ("version", "0.1.0"),
                    ("qualifiers", OrderedDict()),
                    ("subpath", None),
                    ("repository_homepage_url", None),
                    ("repository_download_url", None),
                    ("api_data_url", None),
                    ("primary_language", None),
                    ("description", None),
                    ("release_date", None),
                    ("parties", []),
                    ("keywords", []),
                    ("homepage_url", "https://github.com/nexB/fetchcode"),
                    (
                        "download_url",
                        "https://files.pythonhosted.org/packages/19/a0/c90e5ba4d71ea1a1a89784f6d839ffb0dbf32d270cba04d5602188cb3713/fetchcode-0.1.0-py3-none-any.whl",
                    ),
                    ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                    ("size", None),
                    ("sha1", None),
                    ("md5", None),
                    ("sha256", None),
                    ("sha512", None),
                    ("bug_tracking_url", None),
                    ("code_view_url", None),
                    ("vcs_url", None),
                    ("copyright", None),
                    ("license_expression", None),
                    ("declared_license", "Apache-2.0"),
                    ("notice_text", None),
                    ("root_path", None),
                    ("dependencies", []),
                    ("contains_source_code", None),
                    ("source_packages", []),
                ]
            ),
            OrderedDict(
                [
                    ("purl", "pkg:pypi/fetchcode@0.2.0"),
                    ("type", "pypi"),
                    ("namespace", None),
                    ("name", "fetchcode"),
                    ("version", "0.2.0"),
                    ("qualifiers", OrderedDict()),
                    ("subpath", None),
                    ("repository_homepage_url", None),
                    ("repository_download_url", None),
                    ("api_data_url", None),
                    ("primary_language", None),
                    ("description", None),
                    ("release_date", None),
                    ("parties", []),
                    ("keywords", []),
                    ("homepage_url", "https://github.com/nexB/fetchcode"),
                    (
                        "download_url",
                        "https://files.pythonhosted.org/packages/d7/e9/96e9302e84e326b3c10a40c1723f21f4db96b557a17c6871e7a4c6336906/fetchcode-0.2.0-py3-none-any.whl",
                    ),
                    ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                    ("size", None),
                    ("sha1", None),
                    ("md5", None),
                    ("sha256", None),
                    ("sha512", None),
                    ("bug_tracking_url", None),
                    ("code_view_url", None),
                    ("vcs_url", None),
                    ("copyright", None),
                    ("license_expression", None),
                    ("declared_license", "Apache-2.0"),
                    ("notice_text", None),
                    ("root_path", None),
                    ("dependencies", []),
                    ("contains_source_code", None),
                    ("source_packages", []),
                ]
            ),
            OrderedDict(
                [
                    ("purl", "pkg:pypi/fetchcode@0.3.0"),
                    ("type", "pypi"),
                    ("namespace", None),
                    ("name", "fetchcode"),
                    ("version", "0.3.0"),
                    ("qualifiers", OrderedDict()),
                    ("subpath", None),
                    ("repository_homepage_url", None),
                    ("repository_download_url", None),
                    ("api_data_url", None),
                    ("primary_language", None),
                    ("description", None),
                    ("release_date", None),
                    ("parties", []),
                    ("keywords", []),
                    ("homepage_url", "https://github.com/nexB/fetchcode"),
                    (
                        "download_url",
                        "https://files.pythonhosted.org/packages/8d/fb/e45da0abf63504c3f88ad02537dc9dc64ea5206b09ce29cfb8191420d678/fetchcode-0.3.0-py3-none-any.whl",
                    ),
                    ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                    ("size", None),
                    ("sha1", None),
                    ("md5", None),
                    ("sha256", None),
                    ("sha512", None),
                    ("bug_tracking_url", None),
                    ("code_view_url", None),
                    ("vcs_url", None),
                    ("copyright", None),
                    ("license_expression", None),
                    ("declared_license", "Apache-2.0"),
                    ("notice_text", None),
                    ("root_path", None),
                    ("dependencies", []),
                    ("contains_source_code", None),
                    ("source_packages", []),
                ]
            ),
        ]

        expected_data = {
            "headers": [
                {
                    "tool_name": "purlcli",
                    "tool_version": "0.1.0",
                    "options": {
                        "command": "metadata",
                        "--purl": ["pkg:pypi/fetchcode"],
                        "--file": None,
                        "--output": "",
                    },
                    "errors": [],
                    "warnings": [],
                }
            ],
            "packages": [
                OrderedDict(
                    [
                        ("purl", "pkg:pypi/fetchcode@0.1.0"),
                        ("type", "pypi"),
                        ("namespace", None),
                        ("name", "fetchcode"),
                        ("version", "0.1.0"),
                        ("qualifiers", OrderedDict()),
                        ("subpath", None),
                        ("repository_homepage_url", None),
                        ("repository_download_url", None),
                        ("api_data_url", None),
                        ("primary_language", None),
                        ("description", None),
                        ("release_date", None),
                        ("parties", []),
                        ("keywords", []),
                        ("homepage_url", "https://github.com/nexB/fetchcode"),
                        (
                            "download_url",
                            "https://files.pythonhosted.org/packages/19/a0/c90e5ba4d71ea1a1a89784f6d839ffb0dbf32d270cba04d5602188cb3713/fetchcode-0.1.0-py3-none-any.whl",
                        ),
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
                        ("code_view_url", None),
                        ("vcs_url", None),
                        ("copyright", None),
                        ("license_expression", None),
                        ("declared_license", "Apache-2.0"),
                        ("notice_text", None),
                        ("root_path", None),
                        ("dependencies", []),
                        ("contains_source_code", None),
                        ("source_packages", []),
                    ]
                ),
                OrderedDict(
                    [
                        ("purl", "pkg:pypi/fetchcode@0.2.0"),
                        ("type", "pypi"),
                        ("namespace", None),
                        ("name", "fetchcode"),
                        ("version", "0.2.0"),
                        ("qualifiers", OrderedDict()),
                        ("subpath", None),
                        ("repository_homepage_url", None),
                        ("repository_download_url", None),
                        ("api_data_url", None),
                        ("primary_language", None),
                        ("description", None),
                        ("release_date", None),
                        ("parties", []),
                        ("keywords", []),
                        ("homepage_url", "https://github.com/nexB/fetchcode"),
                        (
                            "download_url",
                            "https://files.pythonhosted.org/packages/d7/e9/96e9302e84e326b3c10a40c1723f21f4db96b557a17c6871e7a4c6336906/fetchcode-0.2.0-py3-none-any.whl",
                        ),
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
                        ("code_view_url", None),
                        ("vcs_url", None),
                        ("copyright", None),
                        ("license_expression", None),
                        ("declared_license", "Apache-2.0"),
                        ("notice_text", None),
                        ("root_path", None),
                        ("dependencies", []),
                        ("contains_source_code", None),
                        ("source_packages", []),
                    ]
                ),
                OrderedDict(
                    [
                        ("purl", "pkg:pypi/fetchcode@0.3.0"),
                        ("type", "pypi"),
                        ("namespace", None),
                        ("name", "fetchcode"),
                        ("version", "0.3.0"),
                        ("qualifiers", OrderedDict()),
                        ("subpath", None),
                        ("repository_homepage_url", None),
                        ("repository_download_url", None),
                        ("api_data_url", None),
                        ("primary_language", None),
                        ("description", None),
                        ("release_date", None),
                        ("parties", []),
                        ("keywords", []),
                        ("homepage_url", "https://github.com/nexB/fetchcode"),
                        (
                            "download_url",
                            "https://files.pythonhosted.org/packages/8d/fb/e45da0abf63504c3f88ad02537dc9dc64ea5206b09ce29cfb8191420d678/fetchcode-0.3.0-py3-none-any.whl",
                        ),
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
                        ("code_view_url", None),
                        ("vcs_url", None),
                        ("copyright", None),
                        ("license_expression", None),
                        ("declared_license", "Apache-2.0"),
                        ("notice_text", None),
                        ("root_path", None),
                        ("dependencies", []),
                        ("contains_source_code", None),
                        ("source_packages", []),
                    ]
                ),
            ],
        }

        input_purls = ["pkg:pypi/fetchcode"]
        output = ""
        file = ""
        command_name = "metadata"

        purl_metadata_data = purlcli.get_metadata_details(
            input_purls,
            output,
            file,
            command_name,
        )

        cli_test_utils.streamline_headers(purl_metadata_data["headers"])
        cli_test_utils.streamline_headers(expected_data["headers"])

        assert purl_metadata_data == expected_data

    def test_deduplicate_purls(self):
        input_purls = [
            "pkg:pypi/fetchcode@0.1.0",
            "pkg:pypi/fetchcode@0.1.0",
            "pkg:pypi/fetchcode@0.1.0",
            "pkg:pypi/fetchcode@0.1.0",
            "pkg:pypi/fetchcode@0.1.0",
            "pkg:pypi/fetchcode@0.2.0",
            "pkg:pypi/fetchcode@0.2.0",
        ]
        actual_output = purlcli.deduplicate_purls(input_purls)
        expected_output = (
            ["pkg:pypi/fetchcode@0.1.0", "pkg:pypi/fetchcode@0.2.0"]
        )
        assert actual_output == expected_output

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                [
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.2.0",
                    "pkg:pypi/fetchcode@0.2.0",
                ],
                [
                    {
                        "errors": [],
                        "options": {
                            "--file": None,
                            "--output": "",
                            "--purl": [
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.2.0",
                                "pkg:pypi/fetchcode@0.2.0",
                            ],
                            "command": "metadata",
                        },
                        "tool_name": "purlcli",
                        "tool_version": "0.1.0",
                        "warnings": [],
                    }
                ],
            ),
        ],
    )
    def test_deduplicate_purls_construct_headers(self, test_input, expected):
        metadata_headers = purlcli.construct_headers(
            test_input,
            output="",
            file="",
            command_name="metadata",
            head=None,
        )

        cli_test_utils.streamline_headers(expected)
        cli_test_utils.streamline_headers(metadata_headers)

        assert metadata_headers == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                [
                    "pkg:gem/bundler-sass",
                    "pkg:pypi/fetchcode",
                    "pkg:pypi/fetchcode@0.1.0",
                    "pkg:pypi/fetchcode@0.2.0",
                ],
                [
                    {
                        "errors": [],
                        "options": {
                            "--file": None,
                            "--output": "",
                            "--purl": [
                                "pkg:gem/bundler-sass",
                                "pkg:pypi/fetchcode",
                                "pkg:pypi/fetchcode@0.1.0",
                                "pkg:pypi/fetchcode@0.2.0",
                            ],
                            "command": "metadata",
                        },
                        "tool_name": "purlcli",
                        "tool_version": "0.1.0",
                        "warnings": [],
                    }
                ],
            ),
        ],
    )
    def test_construct_headers(self, test_input, expected):
        metadata_headers = purlcli.construct_headers(
            test_input,
            output="",
            file="",
            command_name="metadata",
            head=None,
        )

        cli_test_utils.streamline_headers(expected)
        cli_test_utils.streamline_headers(metadata_headers)

        assert metadata_headers == expected


class TestPURLCLI_urls(object):

    @mock.patch("purldb_toolkit.purlcli.make_head_request")
    def test_urls_cli_head(self, mock_make_head_request):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
        mock_make_head_request.side_effect = [
            {"get_request": "N/A"},
            {"head_request": "N/A"},
            {"get_request": "N/A"},
            {"head_request": "N/A"},
            {"get_request": 200},
            {"head_request": 200},
            {"get_request": 200},
            {"head_request": 200},
            {"get_request": 200},
            {"head_request": 200},
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_urls_output_head_mock.json"
        )
        actual_result_file = test_env.get_temp_file("actual_urls_output_head_mock.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--head",
            "--output",
            actual_result_file,
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_urls, options, catch_exceptions=False)
        assert result.exit_code == 0

        with open(actual_result_file) as f_output:
            output_data = json.load(f_output)
            cli_test_utils.streamline_headers(output_data["headers"])

        with open(expected_result_file) as f_expected:
            expected_data = json.load(f_expected)
            cli_test_utils.streamline_headers(expected_data["headers"])

        result_objects = [
            (
                output_data["headers"][0]["tool_name"],
                expected_data["headers"][0]["tool_name"],
            ),
            (
                output_data["headers"][0]["warnings"],
                expected_data["headers"][0]["warnings"],
            ),
            (
                output_data["headers"][0]["errors"],
                expected_data["headers"][0]["errors"],
            ),
            (
                output_data["headers"][0]["options"]["command"],
                expected_data["headers"][0]["options"]["command"],
            ),
            (
                output_data["headers"][0]["options"]["--purl"],
                expected_data["headers"][0]["options"]["--purl"],
            ),
            (
                output_data["headers"][0]["options"]["--file"],
                expected_data["headers"][0]["options"]["--file"],
            ),
            (
                output_data["headers"][0]["options"]["--head"],
                expected_data["headers"][0]["options"]["--head"],
            ),
            (output_data["packages"], expected_data["packages"]),
        ]

        for output, expected in result_objects:
            assert output == expected

    def test_urls_cli_duplicate_input_sources(self):
        """
        Test the `urls` command with both `--purl` and `--file` inputs.
        """
        options = [
            "--purl",
            "pkg:pypi/minecode",
            "--file",
            test_env.get_test_loc("purlcli/metadata_input_purls.txt"),
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_urls, options, catch_exceptions=False)
        assert "Use either purls or file but not both." in result.output
        assert result.exit_code == 2

    def test_urls_cli_no_input_sources(self):
        """
        Test the `urls` command with neither `--purl` nor `--file` inputs.
        """
        options = [
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_urls, options, catch_exceptions=False)
        assert "Use either purls or file." in result.output
        assert result.exit_code == 2

    def test_urls_details(self):
        expected_data = {
            "headers": [
                {
                    "tool_name": "purlcli",
                    "tool_version": "0.1.0",
                    "options": {
                        "command": "urls",
                        "--purl": ["pkg:pypi/fetchcode"],
                        "--file": None,
                        "--output": "",
                    },
                    "errors": [],
                    "warnings": [],
                }
            ],
            "packages": [
                {
                    "purl": "pkg:pypi/fetchcode",
                    "download_url": None,
                    "inferred_urls": [
                        "https://pypi.org/project/fetchcode/",
                    ],
                    "repository_download_url": None,
                    "repository_homepage_url": "https://pypi.org/project/fetchcode/",
                },
            ],
        }

        input_purls = ["pkg:pypi/fetchcode"]

        purl_urls = purlcli.get_urls_details(
            input_purls,
            output="",
            file="",
            command_name="urls",
            head=False,
        )
        cli_test_utils.streamline_headers(expected_data["headers"])
        cli_test_utils.streamline_headers(purl_urls["headers"])

        assert purl_urls == expected_data

    @mock.patch("requests.get")
    @mock.patch("requests.head")
    def test_validate_purl_mock_requests_get_and_head(
        self, mock_requests_head, mock_requests_get
    ):
        get_response = mock.Mock(requests.Response)
        get_response.status_code = 200

        head_response = mock.Mock(requests.Response)
        head_response.status_code = 400

        mock_requests_get.return_value = get_response
        mock_requests_head.return_value = head_response

        expected_results = {"get_request": 200, "head_request": 400}

        url_detail = "https://pypi.org/project/fetchcode/"
        results = purlcli.make_head_request(url_detail)

        assert results == expected_results


class TestPURLCLI_validate(object):

    @mock.patch("requests.get")
    def test_validate_purl_mock_requests_get(self, mock_requests_get):
        mock_request_response = {
            "valid": True,
            "exists": True,
            "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
            "purl": "pkg:pypi/fetchcode",
        }

        def mock_requests_get_return_func():
            return mock_request_response

        mock_requests_get.return_value.json = mock_requests_get_return_func
        input_purl = "pkg:pypi/fetchcode"
        results = purlcli.validate_purl(input_purl)
        assert mock_request_response == results


class TestPURLCLI_versions(object):

    @mock.patch("purldb_toolkit.purlcli.collect_versions")
    def test_versions_details_multiple(self, mock_collect_versions):
        mock_collect_versions.side_effect = [
            [
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.1.0",
                    "release_date": "2021-08-25",
                },
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.2.0",
                    "release_date": "2022-09-14",
                },
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.3.0",
                    "release_date": "2023-12-18",
                },
            ],
            [
                {
                    "purl": "pkg:gem/bundler-sass",
                    "version": "0.1.2",
                    "release_date": "2013-12-11",
                }
            ],
            [
                {
                    "purl": "pkg:cargo/socksprox",
                    "release_date": "2024-02-07",
                    "version": "0.1.1",
                },
                {
                    "purl": "pkg:cargo/socksprox",
                    "release_date": "2024-02-07",
                    "version": "0.1.0",
                },
            ],
        ]

        input_purls_and_expected_purl_data = [
            [
                ["pkg:pypi/fetchcode"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:pypi/fetchcode"],
                                "--file": None,
                                "--output": "",
                            },
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "version": "0.1.0",
                            "release_date": "2021-08-25",
                        },
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "version": "0.2.0",
                            "release_date": "2022-09-14",
                        },
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "version": "0.3.0",
                            "release_date": "2023-12-18",
                        },
                    ],
                },
            ],
            [
                ["pkg:gem/bundler-sass"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:gem/bundler-sass"],
                                "--file": None,
                                "--output": "",
                            },
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:gem/bundler-sass",
                            "version": "0.1.2",
                            "release_date": "2013-12-11",
                        }
                    ],
                },
            ],
            [
                ["pkg:cargo/socksprox"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:cargo/socksprox"],
                                "--file": None,
                                "--output": "",
                            },
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:cargo/socksprox",
                            "version": "0.1.1",
                            "release_date": "2024-02-07",
                        },
                        {
                            "purl": "pkg:cargo/socksprox",
                            "version": "0.1.0",
                            "release_date": "2024-02-07",
                        },
                    ],
                },
            ],
        ]

        output = ""
        file = ""
        command_name = "versions"

        for input_purl, expected_data in input_purls_and_expected_purl_data:
            purl_versions_data = purlcli.get_versions_details(
                input_purl,
                output,
                file,
                command_name,
            )

            assert purl_versions_data == expected_data

    @mock.patch("purldb_toolkit.purlcli.collect_versions")
    def test_versions_details(self, mock_collect_versions):
        mock_collect_versions.return_value = [
            {
                "purl": "pkg:pypi/fetchcode",
                "version": "0.1.0",
                "release_date": "2021-08-25",
            },
            {
                "purl": "pkg:pypi/fetchcode",
                "version": "0.2.0",
                "release_date": "2022-09-14",
            },
            {
                "purl": "pkg:pypi/fetchcode",
                "version": "0.3.0",
                "release_date": "2023-12-18",
            },
        ]

        expected_data = {
            "headers": [
                {
                    "tool_name": "purlcli",
                    "tool_version": "0.2.0",
                    "options": {
                        "command": "versions",
                        "--purl": ["pkg:pypi/fetchcode"],
                        "--file": None,
                        "--output": "",
                    },
                    "errors": [],
                    "warnings": [],
                }
            ],
            "packages": [
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.1.0",
                    "release_date": "2021-08-25",
                },
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.2.0",
                    "release_date": "2022-09-14",
                },
                {
                    "purl": "pkg:pypi/fetchcode",
                    "version": "0.3.0",
                    "release_date": "2023-12-18",
                },
            ],
        }

        input_purls = ["pkg:pypi/fetchcode"]

        output = ""
        file = ""
        command_name = "versions"

        purl_versions_data = purlcli.get_versions_details(
            input_purls,
            output,
            file,
            command_name,
        )
        assert purl_versions_data == expected_data


def streamline_metadata_packages(packages):
    """
    Modify the `packages` list of `metadata` mappings in place to make it easier to test.
    """
    for hle in packages:
        hle.pop("code_view_url", None)
        hle.pop("download_url", None)
