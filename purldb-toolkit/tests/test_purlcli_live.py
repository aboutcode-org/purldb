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
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting
from purldb_toolkit import cli_test_utils
from purldb_toolkit import purlcli

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")

pytestmark = pytest.mark.live_fetch()


class TestPURLCLI_metadata(object):
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_metadata_cli(self, mock_read_log_file):
        """
        Test the `metadata` command with actual and expected JSON output files.

        Note that we can't simply compare the actual and expected JSON files
        because the `--output` values (paths) differ due to the use of
        temporary files, and therefore we test a list of relevant key-value pairs.
        """
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode@0.3.0os=windows' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/fetchcode@5.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:nginx/nginx' not supported with `metadata` command\n",
            "WARNING - 'pkg:gem/rails' not supported with `metadata` command\n",
            "WARNING - 'check_existence' is not supported for 'pkg:rubygems/rails'\n",
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_metadata_output.json"
        )
        actual_result_file = test_env.get_temp_file("actual_metadata_output.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0?os=windows",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0os=windows",
            "--purl",
            "pkg:pypi/fetchcode@5.0.0",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:nginx/nginx",
            "--purl",
            "pkg:gem/rails",
            "--purl",
            "pkg:rubygems/rails",
            "--output",
            actual_result_file,
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_metadata, options, catch_exceptions=False)
        assert result.exit_code == 0

        with open(actual_result_file) as f_output:
            output_data = json.load(f_output)
            cli_test_utils.streamline_headers(output_data["headers"])
            streamline_metadata_packages(output_data["packages"])

        with open(expected_result_file) as f_expected:
            expected_data = json.load(f_expected)
            cli_test_utils.streamline_headers(expected_data["headers"])
            streamline_metadata_packages(expected_data["packages"])

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
        ]

        for output, expected in result_objects:
            assert output == expected

        """
        NOTE: To avoid errors from the addition of new versions, we exclude
        "packages" from the result_objects list above and handle here.  All
        other live-fetch tests are handled in a similar manner.
        """
        compare_packages(expected_data, output_data)

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
        assert "Use either purls or file." in result.output
        assert result.exit_code == 2

    def test_metadata_details(self):
        expected_data = {
            "headers": [
                {
                    "tool_name": "purlcli",
                    "tool_version": "0.2.0",
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
                        ("purl", "pkg:pypi/fetchcode"),
                        ("type", "pypi"),
                        ("namespace", None),
                        ("name", "fetchcode"),
                        ("version", None),
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
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
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
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
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
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
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
                        ("api_url", "https://pypi.org/pypi/fetchcode/json"),
                        ("size", None),
                        ("sha1", None),
                        ("md5", None),
                        ("sha256", None),
                        ("sha512", None),
                        ("bug_tracking_url", None),
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
        streamline_metadata_packages(purl_metadata_data["packages"])

        cli_test_utils.streamline_headers(expected_data["headers"])
        streamline_metadata_packages(expected_data["packages"])

        assert purl_metadata_data["headers"] == expected_data["headers"]
        compare_packages(expected_data, purl_metadata_data)

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                None,
            ),
            (
                ["pkg:gem/bundler-sass"],
                "valid_but_not_supported",
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                "check_existence_not_supported",
            ),
            (
                ["pkg:nginx/nginx"],
                "valid_but_not_supported",
            ),
            (
                ["pkg:pypi/zzzzz"],
                "not_in_upstream_repo",
            ),
            (
                ["pkg:pypi/?fetchcode"],
                "not_valid",
            ),
            (
                ["zzzzz"],
                "not_valid",
            ),
        ],
    )
    def test_check_metadata_purl(self, test_input, expected):
        purl_metadata = purlcli.check_metadata_purl(test_input[0])
        assert purl_metadata == expected

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
                        "tool_version": "0.2.0",
                        "warnings": [
                            "'pkg:gem/bundler-sass' not supported with `metadata` command"
                        ],
                    }
                ],
            ),
        ],
    )
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_construct_headers(self, mock_read_log_file, test_input, expected):
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:gem/bundler-sass' not supported with `metadata` command\n",
        ]

        metadata_headers = purlcli.construct_headers(
            test_input,
            output="",
            file="",
            command_name="metadata",
            head=None,
            purl_warnings={"pkg:gem/bundler-sass": "valid_but_not_supported"},
        )
        cli_test_utils.streamline_headers(expected)
        cli_test_utils.streamline_headers(metadata_headers)

        assert metadata_headers == expected


class TestPURLCLI_urls(object):
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_urls_cli(self, mock_read_log_file):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/fetchcode@0.3.0' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/fetchcode@5.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/dejacode' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0?os=windows' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0os=windows' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0#how/are/you' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@10.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:nginx/nginx' not supported with `urls` command\n",
            "WARNING - 'pkg:nginx/nginx@0.8.9?os=windows' not supported with `urls` command\n",
            "WARNING - 'check_existence' is not supported for 'pkg:rubygems/bundler-sass'\n",
            "WARNING - 'pkg:pypi/matchcode' does not exist in the upstream repo\n",
            "WARNING - 'abcdefg' not valid\n",
            "WARNING - 'pkg/abc' not valid\n",
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_urls_output.json"
        )
        actual_result_file = test_env.get_temp_file("actual_urls_output.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0",
            "--purl",
            "pkg:pypi/fetchcode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode",
            "--purl",
            "pkg:pypi/dejacode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?os=windows",
            "--purl",
            "pkg:pypi/dejacode@5.0.0os=windows",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy",
            "--purl",
            "pkg:pypi/dejacode@5.0.0#how/are/you",
            "--purl",
            "pkg:pypi/dejacode@10.0.0",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:cargo/socksprox",
            "--purl",
            "pkg:nginx/nginx",
            "--purl",
            "pkg:nginx/nginx@0.8.9?os=windows",
            "--purl",
            "pkg:gem/bundler-sass",
            "--purl",
            "pkg:rubygems/bundler-sass",
            "--purl",
            "pkg:pypi/matchcode",
            "--purl",
            "abcdefg",
            "--purl",
            "pkg/abc",
            "--purl",
            "pkg:nuget/auth0-aspnet@1.1.0",
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
            (output_data["packages"], expected_data["packages"]),
        ]

        for output, expected in result_objects:
            assert output == expected

    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_urls_cli_head(self, mock_read_log_file):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/fetchcode@0.3.0' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/fetchcode@5.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/dejacode' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0?os=windows' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0os=windows' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@5.0.0#how/are/you' not fully supported with `urls` command\n",
            "WARNING - 'pkg:pypi/dejacode@10.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:nginx/nginx' not supported with `urls` command\n",
            "WARNING - 'pkg:nginx/nginx@0.8.9?os=windows' not supported with `urls` command\n",
            "WARNING - 'check_existence' is not supported for 'pkg:rubygems/bundler-sass'\n",
            "WARNING - 'pkg:pypi/matchcode' does not exist in the upstream repo\n",
            "WARNING - 'abcdefg' not valid\n",
            "WARNING - 'pkg/abc' not valid\n",
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_urls_output_head.json"
        )
        actual_result_file = test_env.get_temp_file("actual_urls_output_head.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0",
            "--purl",
            "pkg:pypi/fetchcode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode",
            "--purl",
            "pkg:pypi/dejacode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?os=windows",
            "--purl",
            "pkg:pypi/dejacode@5.0.0os=windows",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy",
            "--purl",
            "pkg:pypi/dejacode@5.0.0#how/are/you",
            "--purl",
            "pkg:pypi/dejacode@10.0.0",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:cargo/socksprox",
            "--purl",
            "pkg:nginx/nginx",
            "--purl",
            "pkg:nginx/nginx@0.8.9?os=windows",
            "--purl",
            "pkg:gem/bundler-sass",
            "--purl",
            "pkg:rubygems/bundler-sass",
            "--purl",
            "pkg:pypi/matchcode",
            "--purl",
            "abcdefg",
            "--purl",
            "pkg/abc",
            "--purl",
            "pkg:nuget/auth0-aspnet@1.1.0",
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

    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_urls_details(self, mock_read_log_file):
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode@0.3.0' not fully supported with `urls` command\n",
            "WARNING - 'check_existence' is not supported for 'pkg:github/istio/istio@1.20.2'\n",
        ]

        input_purls = [
            "pkg:pypi/fetchcode@0.3.0",
            "pkg:gem/bundler@2.3.23",
            "pkg:github/istio/istio@1.20.2",
        ]
        output = ""
        file = ""
        command_name = "urls"
        head = False

        purl_urls_data = purlcli.get_urls_details(
            input_purls,
            output,
            file,
            head,
            command_name,
        )

        expected_data = {
            "headers": [
                {
                    "tool_name": "purlcli",
                    "tool_version": "0.2.0",
                    "options": {
                        "command": "urls",
                        "--purl": [
                            "pkg:pypi/fetchcode@0.3.0",
                            "pkg:gem/bundler@2.3.23",
                            "pkg:github/istio/istio@1.20.2",
                        ],
                        "--file": None,
                        "--output": "",
                    },
                    "errors": [],
                    "warnings": [
                        "'pkg:pypi/fetchcode@0.3.0' not fully supported with `urls` command",
                        "'check_existence' is not supported for 'pkg:github/istio/istio@1.20.2'",
                    ],
                }
            ],
            "packages": [
                {
                    "purl": "pkg:pypi/fetchcode@0.3.0",
                    "download_url": {"url": None},
                    "inferred_urls": [
                        {"url": "https://pypi.org/project/fetchcode/0.3.0/"}
                    ],
                    "repo_download_url": {"url": None},
                    "repo_download_url_by_package_type": {"url": None},
                    "repo_url": {"url": "https://pypi.org/project/fetchcode/0.3.0/"},
                },
                {
                    "purl": "pkg:gem/bundler@2.3.23",
                    "download_url": {
                        "url": "https://rubygems.org/downloads/bundler-2.3.23.gem"
                    },
                    "inferred_urls": [
                        {"url": "https://rubygems.org/gems/bundler/versions/2.3.23"},
                        {"url": "https://rubygems.org/downloads/bundler-2.3.23.gem"},
                    ],
                    "repo_download_url": {"url": None},
                    "repo_download_url_by_package_type": {"url": None},
                    "repo_url": {
                        "url": "https://rubygems.org/gems/bundler/versions/2.3.23"
                    },
                },
                {
                    "purl": "pkg:github/istio/istio@1.20.2",
                    "download_url": {
                        "url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz"
                    },
                    "inferred_urls": [
                        {"url": "https://github.com/istio/istio/tree/1.20.2"},
                        {
                            "url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz"
                        },
                    ],
                    "repo_download_url": {
                        "url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz"
                    },
                    "repo_download_url_by_package_type": {
                        "url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz"
                    },
                    "repo_url": {"url": "https://github.com/istio/istio/tree/1.20.2"},
                },
            ],
        }

        assert purl_urls_data == expected_data

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                "valid_but_not_fully_supported",
            ),
            (
                ["pkg:gem/bundler-sass"],
                None,
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                "check_existence_not_supported",
            ),
            (
                ["pkg:nginx/nginx"],
                "valid_but_not_supported",
            ),
            (
                ["pkg:pypi/zzzzz"],
                "not_in_upstream_repo",
            ),
            (
                ["pkg:pypi/?fetchcode"],
                "not_valid",
            ),
            (
                ["zzzzz"],
                "not_valid",
            ),
        ],
    )
    def test_check_urls_purl(self, test_input, expected):
        purl_urls = purlcli.check_urls_purl(test_input[0])
        assert purl_urls == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["https://pypi.org/project/fetchcode/"],
                {"get_request": 200, "head_request": 200},
            ),
            (
                [None],
                {"get_request": "N/A", "head_request": "N/A"},
            ),
            (
                ["https://crates.io/crates/banquo"],
                {"get_request": 404, "head_request": 404},
            ),
            (
                ["https://crates.io/crates/socksprox"],
                {"get_request": 404, "head_request": 404},
            ),
            (
                ["https://www.nuget.org/api/v2/package/auth0-aspnet/1.1.0"],
                {"get_request": 200, "head_request": 404},
            ),
        ],
    )
    def test_make_head_request(self, test_input, expected):
        purl_status_code = purlcli.make_head_request(test_input[0])

        assert purl_status_code == expected


class TestPURLCLI_validate(object):
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_validate_cli(self, mock_read_log_file):
        """
        Test the `validate` command with actual and expected JSON output files.
        """
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode@0.3.0os=windows' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/fetchcode@5.0.0' does not exist in the upstream repo\n",
            "WARNING - 'check_existence' is not supported for 'pkg:nginx/nginx'\n",
            "WARNING - 'check_existence' is not supported for 'pkg:rubygems/rails'\n",
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_validate_output.json"
        )
        actual_result_file = test_env.get_temp_file("actual_validate_output.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0?os=windows",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0os=windows",
            "--purl",
            "pkg:pypi/fetchcode@5.0.0",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:nginx/nginx",
            "--purl",
            "pkg:gem/rails",
            "--purl",
            "pkg:rubygems/rails",
            "--output",
            actual_result_file,
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.validate, options, catch_exceptions=False)
        assert result.exit_code == 0

        with open(actual_result_file) as f_output:
            output_data = json.load(f_output)

        with open(expected_result_file) as f_expected:
            expected_data = json.load(f_expected)

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
            (output_data["packages"], expected_data["packages"]),
        ]

        for output, expected in result_objects:
            assert output == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                "pkg:pypi/fetchcode@0.2.0",
                {
                    "valid": True,
                    "exists": True,
                    "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                    "purl": "pkg:pypi/fetchcode@0.2.0",
                },
            ),
            (
                "pkg:pypi/fetchcode@10.2.0",
                {
                    "valid": True,
                    "exists": False,
                    "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
                    "purl": "pkg:pypi/fetchcode@10.2.0",
                },
            ),
            (
                "pkg:nginx/nginx@0.8.9?os=windows",
                {
                    "valid": True,
                    "exists": None,
                    "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                    "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                },
            ),
            (
                "pkg:gem/bundler-sass",
                {
                    "valid": True,
                    "exists": True,
                    "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                    "purl": "pkg:gem/bundler-sass",
                },
            ),
            (
                "pkg:rubygems/bundler-sass",
                {
                    "valid": True,
                    "exists": None,
                    "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                    "purl": "pkg:rubygems/bundler-sass",
                },
            ),
            (
                "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
                {
                    "valid": True,
                    "exists": True,
                    "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                    "purl": "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
                },
            ),
        ],
    )
    def test_validate_purl(self, test_input, expected):
        validated_purl = purlcli.validate_purl(test_input)
        assert validated_purl == expected

    def test_validate_purl_empty(self):
        test_input = None
        validated_purl = purlcli.validate_purl(test_input)
        expected_results = {"errors": {"purl": ["This field is required."]}}
        assert validated_purl == expected_results

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                "pkg:pypi/fetchcode@0.2.0",
                {
                    "valid": True,
                    "exists": True,
                    "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                    "purl": "pkg:pypi/fetchcode@0.2.0",
                },
            ),
            (
                "pkg:pypi/fetchcode@0.2.0?",
                {
                    "valid": True,
                    "exists": True,
                    "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                    "purl": "pkg:pypi/fetchcode@0.2.0?",
                },
            ),
            (
                "pkg:pypi/fetchcode@?0.2.0",
                {
                    "valid": False,
                    "exists": None,
                    "message": "The provided PackageURL is not valid.",
                    "purl": "pkg:pypi/fetchcode@?0.2.0",
                },
            ),
            (
                "foo",
                {
                    "valid": False,
                    "exists": None,
                    "message": "The provided PackageURL is not valid.",
                    "purl": "foo",
                },
            ),
        ],
    )
    def test_validate_purl_invalid(self, test_input, expected):
        validated_purl = purlcli.validate_purl(test_input)
        assert validated_purl == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                "pkg:nginx/nginx@0.8.9?os=windows",
                {
                    "valid": True,
                    "exists": None,
                    "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                    "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                },
            ),
            (
                " pkg:nginx/nginx@0.8.9?os=windows",
                {
                    "valid": True,
                    "exists": None,
                    "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                    "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                },
            ),
            (
                "pkg:nginx/nginx@0.8.9?os=windows ",
                {
                    "valid": True,
                    "exists": None,
                    "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                    "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                },
            ),
        ],
    )
    def test_validate_purl_strip(self, test_input, expected):
        validated_purl = purlcli.validate_purl(test_input)
        assert validated_purl == expected


class TestPURLCLI_versions(object):
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_versions_cli(self, mock_read_log_file):
        """
        Test the `versions` command with actual and expected JSON output files.
        """
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:pypi/fetchcode@0.3.0os=windows' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/fetchcode@5.0.0' does not exist in the upstream repo\n",
            "WARNING - 'pkg:nginx/nginx' not supported with `versions` command\n",
        ]

        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_versions_output.json"
        )
        actual_result_file = test_env.get_temp_file("actual_versions_output.json")
        options = [
            "--purl",
            "pkg:pypi/fetchcode",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0?os=windows",
            "--purl",
            "pkg:pypi/fetchcode@0.3.0os=windows",
            "--purl",
            "pkg:pypi/fetchcode@5.0.0",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:nginx/nginx",
            "--purl",
            "pkg:hex/coherence@0.1.0",
            "--output",
            actual_result_file,
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_versions, options, catch_exceptions=False)
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
        ]

        for output, expected in result_objects:
            assert output == expected

        compare_packages(expected_data, output_data)

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                [
                    "pkg:pypi/fetchcode",
                    "pkg:gem/bundler-sass",
                    "pkg:rubygems/bundler-sass",
                    "pkg:nginx/nginx",
                    "pkg:pypi/zzzzz",
                    "pkg:pypi/?fetchcode",
                    "zzzzz",
                ],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": [
                                    "pkg:pypi/fetchcode",
                                    "pkg:gem/bundler-sass",
                                    "pkg:rubygems/bundler-sass",
                                    "pkg:nginx/nginx",
                                    "pkg:pypi/zzzzz",
                                    "pkg:pypi/?fetchcode",
                                    "zzzzz",
                                ],
                                "--file": None,
                                "--output": "",
                            },
                            "errors": [],
                            "warnings": [
                                "'pkg:rubygems/bundler-sass' not supported with `versions` command",
                                "'pkg:nginx/nginx' not supported with `versions` command",
                                "'pkg:pypi/zzzzz' does not exist in the upstream repo",
                                "'pkg:pypi/?fetchcode' not valid",
                                "'zzzzz' not valid",
                            ],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:pypi/fetchcode@0.1.0",
                            "version": "0.1.0",
                            "release_date": "2021-08-25",
                        },
                        {
                            "purl": "pkg:pypi/fetchcode@0.2.0",
                            "version": "0.2.0",
                            "release_date": "2022-09-14",
                        },
                        {
                            "purl": "pkg:pypi/fetchcode@0.3.0",
                            "version": "0.3.0",
                            "release_date": "2023-12-18",
                        },
                        {
                            "purl": "pkg:pypi/fetchcode@0.4.0",
                            "release_date": "2024-03-12",
                            "version": "0.4.0",
                        },
                        {
                            "purl": "pkg:gem/bundler-sass@0.1.2",
                            "version": "0.1.2",
                            "release_date": "2013-12-11",
                        },
                    ],
                },
            ),
        ],
    )
    @mock.patch("purldb_toolkit.purlcli.read_log_file")
    def test_versions_details(self, mock_read_log_file, test_input, expected):
        mock_read_log_file.return_value = [
            "WARNING - 'pkg:rubygems/bundler-sass' not supported with `versions` command\n",
            "WARNING - 'pkg:nginx/nginx' not supported with `versions` command\n",
            "WARNING - 'pkg:pypi/zzzzz' does not exist in the upstream repo\n",
            "WARNING - 'pkg:pypi/?fetchcode' not valid\n",
            "WARNING - 'zzzzz' not valid\n",
        ]

        output = ""
        file = ""
        command_name = "versions"

        purl_versions = purlcli.get_versions_details(
            test_input,
            output,
            file,
            command_name,
        )

        cli_test_utils.streamline_headers(purl_versions["headers"])
        cli_test_utils.streamline_headers(expected["headers"])

        assert purl_versions["headers"] == expected["headers"]

        compare_packages(expected, purl_versions)

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                None,
            ),
            (
                ["pkg:gem/bundler-sass"],
                None,
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                "valid_but_not_supported",
            ),
            (
                ["pkg:nginx/nginx"],
                "valid_but_not_supported",
            ),
            (
                ["pkg:pypi/zzzzz"],
                "not_in_upstream_repo",
            ),
            (
                ["pkg:pypi/?fetchcode"],
                "not_valid",
            ),
            (
                ["zzzzz"],
                "not_valid",
            ),
            (
                ["pkg:maven/axis/axis@1.0"],
                None,
            ),
        ],
    )
    def test_check_versions_purl(self, test_input, expected):
        purl_versions = purlcli.check_versions_purl(test_input[0])
        assert purl_versions == expected


def streamline_metadata_packages(packages):
    """
    Modify the `packages` list of `metadata` mappings in place to make it easier to test.
    """
    for hle in packages:
        hle.pop("code_view_url", None)
        hle.pop("download_url", None)


def compare_packages(expected_data, actual_data):
    """
    Compare the expected and actual data nested inside the `packages` field
    returned from a live-fetch query and assert that expected data from prior
    live-fetch queries is found in the data returned by the current live-fetch
    query.  This approach ensures that new data returned by a live fetch, e.g.,
    the addition of new package version data, will not cause the test to fail.
    """
    expected = []
    for expected_pkg in expected_data["packages"]:
        expected.append(expected_pkg)

    actual = []
    for actual_pkg in actual_data["packages"]:
        actual.append(actual_pkg)

    for expected_entry in expected:
        assert expected_entry in actual
