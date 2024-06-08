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
from purldb_toolkit import cli_test_utils
from purldb_toolkit import purlcli

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
                        ("primary_language", None),
                        ("description", None),
                        ("release_date", None),
                        ("parties", []),
                        ("keywords", []),
                        ("homepage_url", "https://github.com/nexB/fetchcode"),
                        ("download_url", None),
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
                        ("repository_homepage_url", None),
                        ("repository_download_url", None),
                        ("api_data_url", None),
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
            "pkg:pypi/dejacode",
            "--purl",
            "pkg:pypi/dejacode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?os=windows",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:cargo/socksprox",
            "--purl",
            "pkg:gem/bundler-sass",
            "--purl",
            "pkg:rubygems/bundler-sass",
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
            "pkg:pypi/dejacode",
            "--purl",
            "pkg:pypi/dejacode@5.0.0",
            "--purl",
            "pkg:pypi/dejacode@5.0.0?os=windows",
            "--purl",
            "pkg:cargo/banquo",
            "--purl",
            "pkg:cargo/socksprox",
            "--purl",
            "pkg:gem/bundler-sass",
            "--purl",
            "pkg:rubygems/bundler-sass",
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

    def test_urls_details(self):
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
                    "warnings": [],
                }
            ],
            "packages": [
                {
                    "purl": "pkg:pypi/fetchcode@0.3.0",
                    "download_url": None,
                    "inferred_urls": [
                        "https://pypi.org/project/fetchcode/0.3.0/",
                    ],
                    "repository_download_url": None,
                    "repository_homepage_url": "https://pypi.org/project/fetchcode/0.3.0/",
                },
                {
                    "purl": "pkg:gem/bundler@2.3.23",
                    "download_url": "https://rubygems.org/downloads/bundler-2.3.23.gem",
                    "inferred_urls": [
                        "https://rubygems.org/gems/bundler/versions/2.3.23",
                        "https://rubygems.org/downloads/bundler-2.3.23.gem",
                    ],
                    "repository_download_url": None,
                    "repository_homepage_url": "https://rubygems.org/gems/bundler/versions/2.3.23",
                },
                {
                    "purl": "pkg:github/istio/istio@1.20.2",
                    "download_url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz",
                    "inferred_urls": [
                        "https://github.com/istio/istio/tree/1.20.2",
                        "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz",
                    ],
                    "repository_download_url": "https://github.com/istio/istio/archive/refs/tags/1.20.2.tar.gz",
                    "repository_homepage_url": "https://github.com/istio/istio/tree/1.20.2",
                },
            ],
        }

        assert purl_urls_data == expected_data

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
                    "pkg:pypi/zzzzz",
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
                                    "pkg:pypi/zzzzz",
                                ],
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
                        {
                            "purl": "pkg:pypi/fetchcode",
                            "release_date": "2024-03-12",
                            "version": "0.4.0",
                        },
                        {
                            "purl": "pkg:gem/bundler-sass",
                            "version": "0.1.2",
                            "release_date": "2013-12-11",
                        },
                    ],
                },
            ),
        ],
    )
    def test_versions_details(self, test_input, expected):
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
