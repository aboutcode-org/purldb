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

import pytest
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting
from purldb_toolkit import cli_test_utils, purlcli

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")

pytestmark = pytest.mark.live_fetch()


class TestPURLCLI_metadata(object):
    def test_metadata_cli(self):
        """
        Test the `metadata` command with actual and expected JSON output files.

        Note that we can't simply compare the actual and expected JSON files
        because the `--output` values (paths) differ due to the use of
        temporary files, and therefore we test a list of relevant key-value pairs.
        """
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

        # NOTE: To avoid errors from the addition of new versions, we exclude
        # "packages" from the result_objects list above and handle here.
        # All other live-fetch tests are handled in a similar manner.

        compare_packages(expected_data, output_data, "metadata")

    def test_metadata_cli_unique(self):
        """
        Test the `metadata` command with actual and expected JSON output files
        with the `--unique` flag included in the command.
        """
        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_metadata_output_unique.json"
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
            "--unique",
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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
                output_data["headers"][0]["options"]["--unique"],
                expected_data["headers"][0]["options"]["--unique"],
            ),
        ]

        for output, expected in result_objects:
            assert output == expected

        compare_packages(expected_data, output_data, "metadata")

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

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                {
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
                            "purls": ["pkg:pypi/fetchcode"],
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "metadata": [
                                OrderedDict(
                                    [
                                        ("purl", "pkg:pypi/fetchcode"),
                                        ("type", "pypi"),
                                        ("namespace", None),
                                        ("name", "fetchcode"),
                                        ("version", None),
                                        ("qualifiers", OrderedDict()),
                                        ("subpath", None),
                                        ("primary_language", None),
                                        ("description", None),
                                        ("release_date", None),
                                        ("parties", []),
                                        ("keywords", []),
                                        (
                                            "homepage_url",
                                            "https://github.com/nexB/fetchcode",
                                        ),
                                        ("download_url", None),
                                        (
                                            "api_url",
                                            "https://pypi.org/pypi/fetchcode/json",
                                        ),
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
                                        ("repository_homepage_url", None),
                                        ("repository_download_url", None),
                                        ("api_data_url", None),
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
                                        ("primary_language", None),
                                        ("description", None),
                                        ("release_date", None),
                                        ("parties", []),
                                        ("keywords", []),
                                        (
                                            "homepage_url",
                                            "https://github.com/nexB/fetchcode",
                                        ),
                                        (
                                            "download_url",
                                            "https://files.pythonhosted.org/packages/19/a0/c90e5ba4d71ea1a1a89784f6d839ffb0dbf32d270cba04d5602188cb3713/fetchcode-0.1.0-py3-none-any.whl",
                                        ),
                                        (
                                            "api_url",
                                            "https://pypi.org/pypi/fetchcode/json",
                                        ),
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
                                        ("repository_homepage_url", None),
                                        ("repository_download_url", None),
                                        ("api_data_url", None),
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
                                        ("primary_language", None),
                                        ("description", None),
                                        ("release_date", None),
                                        ("parties", []),
                                        ("keywords", []),
                                        (
                                            "homepage_url",
                                            "https://github.com/nexB/fetchcode",
                                        ),
                                        (
                                            "download_url",
                                            "https://files.pythonhosted.org/packages/d7/e9/96e9302e84e326b3c10a40c1723f21f4db96b557a17c6871e7a4c6336906/fetchcode-0.2.0-py3-none-any.whl",
                                        ),
                                        (
                                            "api_url",
                                            "https://pypi.org/pypi/fetchcode/json",
                                        ),
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
                                        ("repository_homepage_url", None),
                                        ("repository_download_url", None),
                                        ("api_data_url", None),
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
                                        ("primary_language", None),
                                        ("description", None),
                                        ("release_date", None),
                                        ("parties", []),
                                        ("keywords", []),
                                        (
                                            "homepage_url",
                                            "https://github.com/nexB/fetchcode",
                                        ),
                                        (
                                            "download_url",
                                            "https://files.pythonhosted.org/packages/8d/fb/e45da0abf63504c3f88ad02537dc9dc64ea5206b09ce29cfb8191420d678/fetchcode-0.3.0-py3-none-any.whl",
                                        ),
                                        (
                                            "api_url",
                                            "https://pypi.org/pypi/fetchcode/json",
                                        ),
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
                                        ("repository_homepage_url", None),
                                        ("repository_download_url", None),
                                        ("api_data_url", None),
                                    ]
                                ),
                            ],
                        }
                    ],
                },
            ),
            (
                ["pkg:gem/bundler-sass"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:gem/bundler-sass"],
                                "command": "metadata",
                            },
                            "purls": ["pkg:gem/bundler-sass"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [
                                "'pkg:gem/bundler-sass' not supported with `metadata` command"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "options": {
                                "command": "metadata",
                                "--purl": ["pkg:rubygems/bundler-sass"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:rubygems/bundler-sass"],
                            "errors": [],
                            "warnings": [
                                "'check_existence' is not supported for "
                                "'pkg:rubygems/bundler-sass'",
                            ],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:rubygems/bundler-sass",
                            "metadata": [
                                OrderedDict(
                                    [
                                        ("purl", "pkg:rubygems/bundler-sass"),
                                        ("type", "rubygems"),
                                        ("namespace", None),
                                        ("name", "bundler-sass"),
                                        ("version", None),
                                        ("qualifiers", OrderedDict()),
                                        ("subpath", None),
                                        ("primary_language", None),
                                        ("description", None),
                                        ("release_date", None),
                                        ("parties", []),
                                        ("keywords", []),
                                        (
                                            "homepage_url",
                                            "http://github.com/vogelbek/bundler-sass",
                                        ),
                                        (
                                            "download_url",
                                            "https://rubygems.org/gems/bundler-sass-0.1.2.gem",
                                        ),
                                        (
                                            "api_url",
                                            "https://rubygems.org/api/v1/gems/bundler-sass.json",
                                        ),
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
                                        ("declared_license", ["MIT"]),
                                        ("notice_text", None),
                                        ("root_path", None),
                                        ("dependencies", []),
                                        ("contains_source_code", None),
                                        ("source_packages", []),
                                        ("repository_homepage_url", None),
                                        ("repository_download_url", None),
                                        ("api_data_url", None),
                                    ]
                                )
                            ],
                        }
                    ],
                },
            ),
            (
                ["pkg:nginx/nginx"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:nginx/nginx"],
                                "command": "metadata",
                            },
                            "purls": ["pkg:nginx/nginx"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [
                                "'pkg:nginx/nginx' not supported with `metadata` command"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/zzzzz"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:pypi/zzzzz"],
                                "command": "metadata",
                            },
                            "purls": ["pkg:pypi/zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [
                                "'pkg:pypi/zzzzz' does not exist in the upstream repo",
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/?fetchcode"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:pypi/?fetchcode"],
                                "command": "metadata",
                            },
                            "purls": ["pkg:pypi/?fetchcode"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": ["'pkg:pypi/?fetchcode' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["zzzzz"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["zzzzz"],
                                "command": "metadata",
                            },
                            "purls": ["zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": ["'zzzzz' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
        ],
    )
    def test_metadata_details(self, test_input, expected):
        """
        Test the `metadata` nested function, `get_metadata_details()`.
        """
        purl_metadata = purlcli.get_metadata_details(
            test_input,
            output="",
            file="",
            command_name="metadata",
            unique=False,
        )
        cli_test_utils.streamline_headers(purl_metadata["headers"])
        streamline_metadata_packages(purl_metadata["packages"])

        cli_test_utils.streamline_headers(expected["headers"])
        streamline_metadata_packages(expected["packages"])

        assert purl_metadata["headers"] == expected["headers"]

        compare_packages(expected, purl_metadata, "metadata")

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
        "test_input,expected_input_purls,expected_normalized_purls",
        [
            (
                [["pkg:pypi/fetchcode"]],
                (["pkg:pypi/fetchcode"]),
                ([("pkg:pypi/fetchcode", "pkg:pypi/fetchcode")]),
            ),
            (
                [["pkg:pypi/fetchcode@1.2.3"]],
                (["pkg:pypi/fetchcode"]),
                ([("pkg:pypi/fetchcode@1.2.3", "pkg:pypi/fetchcode")]),
            ),
            (
                [["pkg:pypi/fetchcode@1.2.3?howistheweather=rainy"]],
                (["pkg:pypi/fetchcode"]),
                (
                    [
                        (
                            "pkg:pypi/fetchcode@1.2.3?howistheweather=rainy",
                            "pkg:pypi/fetchcode",
                        )
                    ]
                ),
            ),
            (
                [["pkg:pypi/fetchcode?howistheweather=rainy"]],
                (["pkg:pypi/fetchcode"]),
                ([("pkg:pypi/fetchcode?howistheweather=rainy", "pkg:pypi/fetchcode")]),
            ),
            (
                [["pkg:pypi/fetchcode#this/is/a/path"]],
                (["pkg:pypi/fetchcode"]),
                ([("pkg:pypi/fetchcode#this/is/a/path", "pkg:pypi/fetchcode")]),
            ),
            (
                [["pkg:pypi/?fetchcode"]],
                (["pkg:pypi/"]),
                ([("pkg:pypi/?fetchcode", "pkg:pypi/")]),
            ),
            (
                [
                    [
                        "pkg:pypi/fetchcode@0.3.0",
                        "pkg:pypi/fetchcode@5.0.0",
                        "pkg:pypi/dejacode",
                        "pkg:pypi/dejacode@5.0.0",
                        "pkg:pypi/dejacode@5.0.0?os=windows",
                        "pkg:pypi/dejacode@5.0.0os=windows",
                        "pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy",
                        "pkg:pypi/dejacode@5.0.0#how/are/you",
                        "pkg:pypi/dejacode@10.0.0",
                        "pkg:cargo/banquo",
                        "pkg:cargo/socksprox",
                        "pkg:nginx/nginx",
                        "pkg:nginx/nginx@0.8.9?os=windows",
                    ]
                ],
                (
                    [
                        "pkg:pypi/fetchcode",
                        "pkg:pypi/dejacode",
                        "pkg:cargo/banquo",
                        "pkg:cargo/socksprox",
                        "pkg:nginx/nginx",
                    ]
                ),
                (
                    [
                        ("pkg:pypi/fetchcode@0.3.0", "pkg:pypi/fetchcode"),
                        ("pkg:pypi/fetchcode@5.0.0", "pkg:pypi/fetchcode"),
                        ("pkg:pypi/dejacode", "pkg:pypi/dejacode"),
                        ("pkg:pypi/dejacode@5.0.0", "pkg:pypi/dejacode"),
                        ("pkg:pypi/dejacode@5.0.0?os=windows", "pkg:pypi/dejacode"),
                        ("pkg:pypi/dejacode@5.0.0os=windows", "pkg:pypi/dejacode"),
                        (
                            "pkg:pypi/dejacode@5.0.0?how_is_the_weather=rainy",
                            "pkg:pypi/dejacode",
                        ),
                        ("pkg:pypi/dejacode@5.0.0#how/are/you", "pkg:pypi/dejacode"),
                        ("pkg:pypi/dejacode@10.0.0", "pkg:pypi/dejacode"),
                        ("pkg:cargo/banquo", "pkg:cargo/banquo"),
                        ("pkg:cargo/socksprox", "pkg:cargo/socksprox"),
                        ("pkg:nginx/nginx", "pkg:nginx/nginx"),
                        ("pkg:nginx/nginx@0.8.9?os=windows", "pkg:nginx/nginx"),
                    ]
                ),
            ),
        ],
    )
    def test_normalize_purls(
        self, test_input, expected_input_purls, expected_normalized_purls
    ):
        unique = True
        input_purls, normalized_purls = purlcli.normalize_purls(test_input[0], unique)

        assert input_purls == expected_input_purls
        assert normalized_purls == expected_normalized_purls

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
                        "purls": [
                            "pkg:gem/bundler-sass",
                            "pkg:pypi/fetchcode",
                            "pkg:pypi/fetchcode@0.1.0",
                            "pkg:pypi/fetchcode@0.2.0",
                        ],
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
    def test_construct_headers(self, test_input, expected):
        metadata_headers = purlcli.construct_headers(
            test_input,
            output="",
            file="",
            command_name="metadata",
            head=None,
            normalized_purls=None,
            unique=None,
            purl_warnings={"pkg:gem/bundler-sass": "valid_but_not_supported"},
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
                            "--unique": True,
                            "command": "metadata",
                        },
                        "purls": [
                            "pkg:gem/bundler-sass",
                            "pkg:pypi/fetchcode",
                            "pkg:pypi/fetchcode@0.1.0",
                            "pkg:pypi/fetchcode@0.2.0",
                        ],
                        "tool_name": "purlcli",
                        "tool_version": "0.2.0",
                        "warnings": [
                            "input PURL: 'pkg:pypi/fetchcode@0.1.0' normalized to 'pkg:pypi/fetchcode'",
                            "input PURL: 'pkg:pypi/fetchcode@0.2.0' normalized to 'pkg:pypi/fetchcode'",
                            "'pkg:gem/bundler-sass' not supported with `metadata` command",
                        ],
                    }
                ],
            ),
        ],
    )
    def test_construct_headers_unique(self, test_input, expected):
        metadata_headers = purlcli.construct_headers(
            test_input,
            output="",
            file="",
            command_name="metadata",
            head=None,
            normalized_purls=[
                ("pkg:gem/bundler-sass", "pkg:gem/bundler-sass"),
                ("pkg:pypi/fetchcode", "pkg:pypi/fetchcode"),
                ("pkg:pypi/fetchcode@0.1.0", "pkg:pypi/fetchcode"),
                ("pkg:pypi/fetchcode@0.2.0", "pkg:pypi/fetchcode"),
            ],
            unique=True,
            purl_warnings={"pkg:gem/bundler-sass": "valid_but_not_supported"},
        )
        cli_test_utils.streamline_headers(expected)
        cli_test_utils.streamline_headers(metadata_headers)

        assert metadata_headers == expected


class TestPURLCLI_urls(object):
    def test_urls_cli(self):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

    def test_urls_cli_unique(self):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_urls_output_unique.json"
        )
        actual_result_file = test_env.get_temp_file("actual_urls_output_unique.json")
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
            "--unique",
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

    def test_urls_cli_head(self):
        """
        Test the `urls` command with actual and expected JSON output files.
        """
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "urls",
                                "--purl": ["pkg:pypi/fetchcode"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:pypi/fetchcode"],
                            "errors": [],
                            "warnings": [
                                "'pkg:pypi/fetchcode' not fully supported with `urls` command"
                            ],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "download_url": {
                                "url": None,
                            },
                            "inferred_urls": [
                                {
                                    "url": "https://pypi.org/project/fetchcode/",
                                }
                            ],
                            "repo_download_url": {
                                "url": None,
                            },
                            "repo_download_url_by_package_type": {
                                "url": None,
                            },
                            "repo_url": {
                                "url": "https://pypi.org/project/fetchcode/",
                            },
                            "url": {
                                "url": "https://pypi.org/project/fetchcode/",
                            },
                        },
                    ],
                },
            ),
            (
                ["pkg:pypi/fetchcode@10.0.0"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "urls",
                                "--purl": ["pkg:pypi/fetchcode@10.0.0"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:pypi/fetchcode@10.0.0"],
                            "errors": [],
                            "warnings": [
                                "'pkg:pypi/fetchcode@10.0.0' does not exist in the upstream repo",
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:gem/bundler-sass"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:gem/bundler-sass"],
                                "command": "urls",
                            },
                            "purls": ["pkg:gem/bundler-sass"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:gem/bundler-sass",
                            "download_url": {
                                "url": None,
                            },
                            "inferred_urls": [
                                {
                                    "url": "https://rubygems.org/gems/bundler-sass",
                                }
                            ],
                            "repo_download_url": {
                                "url": None,
                            },
                            "repo_download_url_by_package_type": {
                                "url": None,
                            },
                            "repo_url": {
                                "url": "https://rubygems.org/gems/bundler-sass",
                            },
                            "url": {
                                "url": "https://rubygems.org/gems/bundler-sass",
                            },
                        },
                    ],
                },
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:rubygems/bundler-sass"],
                                "command": "urls",
                            },
                            "purls": ["pkg:rubygems/bundler-sass"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:rubygems/bundler-sass",
                            "download_url": {
                                "url": None,
                            },
                            "inferred_urls": [
                                {
                                    "url": "https://rubygems.org/gems/bundler-sass",
                                }
                            ],
                            "repo_download_url": {
                                "url": None,
                            },
                            "repo_download_url_by_package_type": {
                                "url": None,
                            },
                            "repo_url": {
                                "url": "https://rubygems.org/gems/bundler-sass",
                            },
                            "url": {
                                "url": "https://rubygems.org/gems/bundler-sass",
                            },
                        },
                    ],
                },
            ),
            (
                ["pkg:nginx/nginx"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:nginx/nginx"],
                                "command": "urls",
                            },
                            "purls": ["pkg:nginx/nginx"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [
                                "'pkg:nginx/nginx' not supported with `urls` command"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/zzzzz"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:pypi/zzzzz"],
                                "command": "urls",
                            },
                            "purls": ["pkg:pypi/zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": [
                                "'pkg:pypi/zzzzz' does not exist in the upstream repo",
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/?fetchcode"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:pypi/?fetchcode"],
                                "command": "urls",
                            },
                            "purls": ["pkg:pypi/?fetchcode"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": ["'pkg:pypi/?fetchcode' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["zzzzz"],
                {
                    "headers": [
                        {
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["zzzzz"],
                                "command": "urls",
                            },
                            "purls": ["zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "warnings": ["'zzzzz' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
        ],
    )
    def test_urls_details(self, test_input, expected):
        """
        Test the `urls` nested function, `get_urls_details()`.
        """
        purl_urls = purlcli.get_urls_details(
            test_input,
            output="",
            file="",
            command_name="urls",
            head=False,
            unique=False,
        )
        cli_test_utils.streamline_headers(expected["headers"])
        cli_test_utils.streamline_headers(purl_urls["headers"])

        assert purl_urls == expected

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
                None,
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
    def test_validate_cli(self):
        """
        Test the `validate` command with actual and expected JSON output files.
        """
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

    def test_validate_cli_unique(self):
        """
        Test the `validate` command with actual and expected JSON output files
        with the `--unique` flag included in the command.
        """
        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_validate_output_unique.json"
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
            "--unique",
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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
                output_data["headers"][0]["options"]["--unique"],
                expected_data["headers"][0]["options"]["--unique"],
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
    def test_versions_cli(self):
        """
        Test the `versions` command with actual and expected JSON output files.
        """
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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

        compare_packages(expected_data, output_data, "versions")

    def test_versions_cli_unique(self):
        """
        Test the `versions` command with actual and expected JSON output files
        with the `--unique` flag included in the command.
        """
        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_versions_output_unique.json"
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
            "--unique",
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
            (output_data["headers"][0]["purls"], expected_data["headers"][0]["purls"]),
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
                output_data["headers"][0]["options"]["--unique"],
                expected_data["headers"][0]["options"]["--unique"],
            ),
        ]

        for output, expected in result_objects:
            assert output == expected

        compare_packages(expected_data, output_data, "versions")

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
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
                            "purls": ["pkg:pypi/fetchcode"],
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "versions": [
                                {
                                    "purl": "pkg:pypi/fetchcode@0.1.0",
                                    "version": "0.1.0",
                                    "release_date": "2021-08-25 15:15:15.265015+00:00",
                                },
                                {
                                    "purl": "pkg:pypi/fetchcode@0.2.0",
                                    "version": "0.2.0",
                                    "release_date": "2022-09-14 16:36:02.242182+00:00",
                                },
                                {
                                    "purl": "pkg:pypi/fetchcode@0.3.0",
                                    "version": "0.3.0",
                                    "release_date": "2023-12-18 20:49:45.840364+00:00",
                                },
                                {
                                    "purl": "pkg:pypi/fetchcode@0.4.0",
                                    "release_date": "2024-03-12 07:01:29.239299+00:00",
                                    "version": "0.4.0",
                                },
                            ],
                        }
                    ],
                },
            ),
            (
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
                            "purls": ["pkg:gem/bundler-sass"],
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:gem/bundler-sass",
                            "versions": [
                                {
                                    "purl": "pkg:gem/bundler-sass@0.1.2",
                                    "version": "0.1.2",
                                    "release_date": "2013-12-11 00:27:10.097000+00:00",
                                }
                            ],
                        }
                    ],
                },
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:rubygems/bundler-sass"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:rubygems/bundler-sass"],
                            "errors": [],
                            "warnings": [
                                "'pkg:rubygems/bundler-sass' not supported with `versions` command"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:nginx/nginx"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:nginx/nginx"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:nginx/nginx"],
                            "errors": [],
                            "warnings": [
                                "'pkg:nginx/nginx' not supported with `versions` command"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/zzzzz"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:pypi/zzzzz"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:pypi/zzzzz"],
                            "errors": [],
                            "warnings": [
                                "'pkg:pypi/zzzzz' does not exist in the upstream repo"
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["pkg:pypi/?fetchcode"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["pkg:pypi/?fetchcode"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["pkg:pypi/?fetchcode"],
                            "errors": [],
                            "warnings": ["'pkg:pypi/?fetchcode' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
            (
                ["zzzzz"],
                {
                    "headers": [
                        {
                            "tool_name": "purlcli",
                            "tool_version": "0.2.0",
                            "options": {
                                "command": "versions",
                                "--purl": ["zzzzz"],
                                "--file": None,
                                "--output": "",
                            },
                            "purls": ["zzzzz"],
                            "errors": [],
                            "warnings": ["'zzzzz' not valid"],
                        }
                    ],
                    "packages": [],
                },
            ),
        ],
    )
    def test_versions_details(self, test_input, expected):
        output = ""
        file = ""
        command_name = "versions"
        unique = False

        purl_versions = purlcli.get_versions_details(
            test_input, output, file, unique, command_name
        )

        cli_test_utils.streamline_headers(purl_versions["headers"])
        cli_test_utils.streamline_headers(expected["headers"])

        assert purl_versions["headers"] == expected["headers"]

        compare_packages(expected, purl_versions, "versions")

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


def compare_packages(expected_data, actual_data, nested_key):
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
        for actual_entry in actual:
            if expected_entry["purl"] == actual_entry["purl"]:
                for expected_sibling in expected_entry[nested_key]:
                    assert expected_sibling in actual_entry[nested_key]
