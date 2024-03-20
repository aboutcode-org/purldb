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
from purldb_toolkit import cli_test_utils, purlcli

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


class TestPURLCLI_metadata(object):
    # NOTE: Looks OK.
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

    # NOTE: Looks OK.
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

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.collect_metadata")
    @mock.patch("purldb_toolkit.purlcli.check_metadata_purl")
    def test_metadata_details(self, mock_check_metadata_purl, mock_collect_metadata):

        mock_collect_metadata.return_value = [
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
        ]

        mock_check_metadata_purl.return_value = None

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
            ],
        }

        input_purls = ["pkg:pypi/fetchcode"]

        output = ""
        file = ""
        command_name = "metadata"
        unique = False

        purl_metadata_data = purlcli.get_metadata_details(
            input_purls,
            output,
            file,
            unique,
            command_name,
        )

        cli_test_utils.streamline_headers(purl_metadata_data["headers"])
        cli_test_utils.streamline_headers(expected_data["headers"])

        assert purl_metadata_data == expected_data

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.validate_purl")
    def test_check_metadata_purl(self, mock_validate_purl):
        mock_validate_purl.return_value = {
            "valid": True,
            "exists": None,
            "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
            "purl": "pkg:rubygems/bundler-sass",
        }
        input_purl = "pkg:rubygems/bundler-sass"
        expected = "check_existence_not_supported"
        purl_metadata = purlcli.check_metadata_purl(input_purl)

        assert purl_metadata == expected

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.validate_purl")
    def test_check_metadata_purl_multiple(self, mock_validate_purl):
        mock_validate_purl.side_effect = [
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:pypi/fetchcode",
            },
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:gem/bundler-sass",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:rubygems/bundler-sass",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx",
            },
            {
                "valid": True,
                "exists": False,
                "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
                "purl": "pkg:pypi/zzzzz",
            },
            {
                "valid": False,
                "exists": None,
                "message": "The provided PackageURL is not valid.",
                "purl": "pkg:pypi/?fetchcode",
            },
            {
                "valid": False,
                "exists": None,
                "message": "The provided PackageURL is not valid.",
                "purl": "zzzzz",
            },
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:maven/axis/axis@1.0",
            },
        ]

        input_purls_and_expected_states = [
            ["pkg:pypi/fetchcode", None],
            ["pkg:gem/bundler-sass", "valid_but_not_supported"],
            ["pkg:rubygems/bundler-sass", "check_existence_not_supported"],
            ["pkg:nginx/nginx", "valid_but_not_supported"],
            ["pkg:pypi/zzzzz", "not_in_upstream_repo"],
            ["pkg:pypi/?fetchcode", "not_valid"],
            ["zzzzz", "not_valid"],
            ["pkg:maven/axis/axis@1.0", "valid_but_not_supported"],
        ]

        for input_purl, expected_state in input_purls_and_expected_states:
            purl_metadata = purlcli.check_metadata_purl(input_purl)
            assert purl_metadata == expected_state

    # NOTE: Looks OK.
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

    # NOTE: Looks OK.
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
                        "tool_version": "0.1.0",
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

    # NOTE: Looks OK.
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
                        "tool_version": "0.1.0",
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
    # NOTE: This works.  ;-)
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

        f_output = open(actual_result_file)
        output_data = json.load(f_output)
        cli_test_utils.streamline_headers(output_data["headers"])

        f_expected = open(expected_result_file)
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

    # NOTE: Looks OK.
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

    # NOTE: Looks OK.
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

    # NOTE: 2024-03-18 Monday 22:07:52.  This works!
    @mock.patch("purldb_toolkit.purlcli.check_urls_purl")
    def test_urls_details(self, mock_check_urls_purl):
        mock_check_urls_purl.return_value = "valid_but_not_fully_supported"

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
        }

        input_purls = ["pkg:pypi/fetchcode"]

        purl_urls = purlcli.get_urls_details(
            input_purls,
            output="",
            file="",
            command_name="urls",
            head=False,
            unique=False,
        )
        cli_test_utils.streamline_headers(expected_data["headers"])
        cli_test_utils.streamline_headers(purl_urls["headers"])

        assert purl_urls == expected_data

    # NOTE: This works!
    @mock.patch("purldb_toolkit.purlcli.validate_purl")
    def test_check_urls_purl(self, mock_validate_purl):
        mock_validate_purl.return_value = {
            "valid": True,
            "exists": True,
            "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
            "purl": "pkg:pypi/fetchcode",
        }

        input_purl = "pkg:pypi/fetchcode"
        expected = "valid_but_not_fully_supported"
        purl_urls = purlcli.check_urls_purl(input_purl)

        assert purl_urls == expected


class TestPURLCLI_validate(object):

    # # This is a test of mocking `validate_purl` itself.  But this is circular and really proves nothing, right?
    # @mock.patch("purldb_toolkit.purlcli.validate_purl")
    # # def test_validate_purl_mock(self, test_input, expected):
    # def test_validate_purl_mock(self, mock_validate_purl):
    #     mock_validate_purl.return_value = {
    #         "valid": True,
    #         "exists": None,
    #         "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
    #         "purl": "pkg:rubygems/bundler-sass",
    #     }
    #     input_purl = "pkg:rubygems/bundler-sass"

    #     expected = {
    #         "valid": True,
    #         "exists": None,
    #         "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
    #         "purl": "pkg:rubygems/bundler-sass",
    #     }

    #     validated_purl = purlcli.validate_purl(input_purl)

    #     assert validated_purl == expected

    def test_validate_purl_mock_01(self):
        with mock.patch("requests.get") as mock_request:
            # url = 'http://google.com'
            input_purl = "pkg:rubygems/bundler-sass"

            # set a `status_code` attribute on the mock object
            # with value 200
            mock_request.return_value.status_code = 200
            mock_request.return_value.text = {"blah": "blah"}

            mock_request = mock.Mock(
                return_value=mock.Mock(status_code=200, text='{"blah": "blah"}')
            )

            mock_app = mock.MagicMock()
            mock_app.get().json().return_value = {"fruit": "apple"}

            # self.assertTrue(url_exists(url))

            print(
                f"\npurlcli.validate_purl(input_purl) = {purlcli.validate_purl(input_purl)}"
            )

    # NOTE: These 3 are the current live-fetch tests, each of which calls `validate_purl()`.

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
    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.collect_versions")
    @mock.patch("purldb_toolkit.purlcli.check_versions_purl")
    def test_versions_details_multiple(
        self,
        mock_check_versions_purl,
        mock_collect_versions,
    ):

        mock_check_versions_purl.side_effect = [
            None,
            None,
            "valid_but_not_supported",
            "valid_but_not_supported",
            None,
            "not_valid",
        ]

        mock_collect_versions.side_effect = [
            [
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
            ],
            [
                {
                    "purl": "pkg:gem/bundler-sass@0.1.2",
                    "version": "0.1.2",
                    "release_date": "2013-12-11 00:27:10.097000+00:00",
                }
            ],
            [
                {
                    "purl": "pkg:cargo/socksprox@0.1.1",
                    "release_date": "2024-02-07 23:29:58.801293+00:00",
                    "version": "0.1.1",
                },
                {
                    "purl": "pkg:cargo/socksprox@0.1.0",
                    "release_date": "2024-02-07 23:21:05.242366+00:00",
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
                            ],
                        }
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
            ],
            [
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
            ],
            [
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
                            "purls": ["pkg:cargo/socksprox"],
                            "errors": [],
                            "warnings": [],
                        }
                    ],
                    "packages": [
                        {
                            "purl": "pkg:cargo/socksprox",
                            "versions": [
                                {
                                    "purl": "pkg:cargo/socksprox@0.1.1",
                                    "version": "0.1.1",
                                    "release_date": "2024-02-07 23:29:58.801293+00:00",
                                },
                                {
                                    "purl": "pkg:cargo/socksprox@0.1.0",
                                    "version": "0.1.0",
                                    "release_date": "2024-02-07 23:21:05.242366+00:00",
                                },
                            ],
                        }
                    ],
                },
            ],
            [
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
            ],
        ]

        output = ""
        file = ""
        command_name = "versions"
        unique = False

        for input_purl, expected_data in input_purls_and_expected_purl_data:
            purl_versions_data = purlcli.get_versions_details(
                input_purl, output, file, unique, command_name
            )

            assert purl_versions_data == expected_data

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.collect_versions")
    @mock.patch("purldb_toolkit.purlcli.check_versions_purl")
    def test_versions_details(
        self,
        mock_check_versions_purl,
        mock_collect_versions,
    ):

        mock_collect_versions.return_value = [
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
        ]

        mock_check_versions_purl.return_value = None

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
                    ],
                }
            ],
        }

        input_purls = ["pkg:pypi/fetchcode"]

        output = ""
        file = ""
        command_name = "versions"
        unique = False

        purl_versions_data = purlcli.get_versions_details(
            input_purls,
            output,
            file,
            unique,
            command_name,
        )
        assert purl_versions_data == expected_data

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.validate_purl")
    def test_check_versions_purl_multiple(self, mock_validate_purl):
        mock_validate_purl.side_effect = [
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:pypi/fetchcode",
            },
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:gem/bundler-sass",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:rubygems/bundler-sass",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx",
            },
            {
                "valid": True,
                "exists": False,
                "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
                "purl": "pkg:pypi/zzzzz",
            },
            {
                "valid": False,
                "exists": None,
                "message": "The provided PackageURL is not valid.",
                "purl": "pkg:pypi/?fetchcode",
            },
            {
                "valid": False,
                "exists": None,
                "message": "The provided PackageURL is not valid.",
                "purl": "zzzzz",
            },
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:maven/axis/axis@1.0",
            },
        ]
        input_purls_and_expected_states = [
            ["pkg:pypi/fetchcode", None],
            ["pkg:gem/bundler-sass", None],
            ["pkg:rubygems/bundler-sass", "valid_but_not_supported"],
            ["pkg:nginx/nginx", "valid_but_not_supported"],
            ["pkg:pypi/zzzzz", "not_in_upstream_repo"],
            ["pkg:pypi/?fetchcode", "not_valid"],
            ["zzzzz", "not_valid"],
            ["pkg:maven/axis/axis@1.0", None],
        ]
        for input_purl, expected_state in input_purls_and_expected_states:
            purl_versions = purlcli.check_versions_purl(input_purl)
            assert purl_versions == expected_state

    # NOTE: This works.
    @mock.patch("purldb_toolkit.purlcli.validate_purl")
    def test_check_versions_purl(self, mock_validate_purl):
        mock_validate_purl.return_value = {
            "valid": True,
            "exists": None,
            "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
            "purl": "pkg:rubygems/bundler-sass",
        }
        input_purl = "pkg:rubygems/bundler-sass"
        purl_versions = purlcli.check_versions_purl(input_purl)
        expected = "valid_but_not_supported"
        assert purl_versions == expected


def streamline_metadata_packages(packages):
    """
    Modify the `packages` list of `metadata` mappings in place to make it easier to test.
    """
    for hle in packages:
        hle.pop("code_view_url", None)
        hle.pop("download_url", None)
