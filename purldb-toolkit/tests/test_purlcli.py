import json
import os
from collections import OrderedDict

import click
import pytest
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting
from purldb_toolkit import purlcli

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


class TestPURLCLI_meta(object):
    def test_meta_cli(self):
        """
        Test the `meta` command with actual and expected JSON output files.
        Note that we can't simply compare the actual and expected JSON files
        because the `--output` values (paths) differ due to the use of
        temporary files, and therefore we test a list of relevant key-value pairs.
        """
        expected_result_file = test_env.get_test_loc(
            "purlcli/expected_meta_output.json"
        )
        actual_result_file = test_env.get_temp_file("actual_meta_output.json")
        options = [
            "--purl",
            "pkg:pypi/minecode",
            "--output",
            actual_result_file,
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_meta, options, catch_exceptions=False)
        assert result.exit_code == 0

        f_output = open(actual_result_file)
        output_data = json.load(f_output)

        f_expected = open(expected_result_file)
        expected_data = json.load(f_expected)

        result_objects = [
            (
                output_data["headers"][0]["tool_name"],
                expected_data["headers"][0]["tool_name"],
            ),
            (
                output_data["headers"][0]["tool_version"],
                expected_data["headers"][0]["tool_version"],
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

    def test_meta_cli_duplicate_input_sources(self):
        """
        Test the `meta` command with both `--purl` and `--file` inputs.
        """
        options = [
            "--purl",
            "pkg:pypi/minecode",
            "--file",
            # "meta_input_purls.txt",
            "purldb-toolkit/tests/data/purlcli/meta_input_purls.txt",
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_meta, options, catch_exceptions=False)
        assert "Use either purls or file but not both." in result.output
        assert result.exit_code == 2

    def test_meta_cli_no_input_sources(self):
        """
        Test the `meta` command with neither `--purl` nor `--file` inputs.
        """
        options = [
            "--output",
            "-",
        ]
        runner = CliRunner()
        result = runner.invoke(purlcli.get_meta, options, catch_exceptions=False)
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
                            "tool_version": "0.0.1",
                            "options": {
                                "command": "meta",
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
                                "command": "meta",
                            },
                            "purls": ["pkg:gem/bundler-sass"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "The provided PackageURL 'pkg:gem/bundler-sass' is "
                                "valid, but `meta` is not supported for this "
                                "package type."
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
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:rubygems/bundler-sass"],
                                "command": "meta",
                            },
                            "purls": ["pkg:rubygems/bundler-sass"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "There was an error with your 'pkg:rubygems/bundler-sass' "
                                "query.  Make sure that 'pkg:rubygems/bundler-sass' actually "
                                "exists in the relevant repository.",
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
                            "errors": [],
                            "options": {
                                "--file": None,
                                "--output": "",
                                "--purl": ["pkg:nginx/nginx"],
                                "command": "meta",
                            },
                            "purls": ["pkg:nginx/nginx"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "The provided PackageURL 'pkg:nginx/nginx' is "
                                "valid, but `meta` is not supported for this "
                                "package type."
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
                                "command": "meta",
                            },
                            "purls": ["pkg:pypi/zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "There was an error with your 'pkg:pypi/zzzzz' "
                                "query.  Make sure that 'pkg:pypi/zzzzz' actually "
                                "exists in the relevant repository.",
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
                                "command": "meta",
                            },
                            "purls": ["pkg:pypi/?fetchcode"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "There was an error with your 'pkg:pypi/?fetchcode' query -- the "
                                "Package URL you provided is not valid."
                            ],
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
                                "command": "meta",
                            },
                            "purls": ["zzzzz"],
                            "tool_name": "purlcli",
                            "tool_version": "0.0.1",
                            "warnings": [
                                "There was an error with your 'zzzzz' query -- the "
                                "Package URL you provided is not valid."
                            ],
                        }
                    ],
                    "packages": [],
                },
            ),
        ],
    )
    def test_meta_details(self, test_input, expected):
        """
        Test the `meta` nested function, `get_meta_details()`.
        """
        purl_meta = purlcli.get_meta_details(
            test_input, output="", file="", manual_command_name="meta"
        )
        assert purl_meta == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                None,
            ),
            (
                ["pkg:gem/bundler-sass"],
                "The provided PackageURL 'pkg:gem/bundler-sass' is valid, but `meta` is not supported for this package type.",
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                "There was an error with your 'pkg:rubygems/bundler-sass' query.  Make sure that 'pkg:rubygems/bundler-sass' actually exists in the relevant repository.",
            ),
            (
                ["pkg:nginx/nginx"],
                "The provided PackageURL 'pkg:nginx/nginx' is valid, but `meta` is not supported for this package type.",
            ),
            (
                ["pkg:pypi/zzzzz"],
                "There was an error with your 'pkg:pypi/zzzzz' query.  Make sure that 'pkg:pypi/zzzzz' actually exists in the relevant repository.",
            ),
            (
                ["pkg:pypi/?fetchcode"],
                "There was an error with your 'pkg:pypi/?fetchcode' query -- the Package URL you provided is not valid.",
            ),
            (
                ["zzzzz"],
                "There was an error with your 'zzzzz' query -- the Package URL you provided is not valid.",
            ),
        ],
    )
    def test_check_meta_purl(self, test_input, expected):
        purl_meta = purlcli.check_meta_purl(test_input[0])
        assert purl_meta == expected


# To come once I've converted the output to a SCTK-like data structure.
# class TestPURLCLI_urls(object):
# xxx


# These tests and the underlying code have not yet been converted to a SCTK-like data structure.
class TestPURLCLI_validate(object):
    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode@0.2.0"],
                [
                    {
                        "valid": True,
                        "exists": True,
                        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                        "purl": "pkg:pypi/fetchcode@0.2.0",
                    }
                ],
            ),
            (
                ["pkg:pypi/fetchcode@10.2.0"],
                [
                    {
                        "valid": True,
                        "exists": False,
                        "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
                        "purl": "pkg:pypi/fetchcode@10.2.0",
                    }
                ],
            ),
            (
                ["pkg:nginx/nginx@0.8.9?os=windows"],
                [
                    {
                        "valid": True,
                        "exists": None,
                        "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                        "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                    }
                ],
            ),
            (
                ["pkg:gem/bundler-sass"],
                [
                    {
                        "valid": True,
                        "exists": True,
                        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                        "purl": "pkg:gem/bundler-sass",
                    }
                ],
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                [
                    {
                        "valid": True,
                        "exists": None,
                        "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                        "purl": "pkg:rubygems/bundler-sass",
                    }
                ],
            ),
            (
                ["pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1"],
                [
                    {
                        "valid": True,
                        "exists": True,
                        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                        "purl": "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
                    }
                ],
            ),
        ],
    )
    def test_validate_purl(self, test_input, expected):
        validated_purls = purlcli.validate_purls(test_input)
        assert validated_purls == expected

    def test_validate_purl_empty(self):
        test_purls = []
        validated_purls = purlcli.validate_purls(test_purls)
        expected_results = []
        assert validated_purls == expected_results

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode@0.2.0"],
                [
                    {
                        "valid": True,
                        "exists": True,
                        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                        "purl": "pkg:pypi/fetchcode@0.2.0",
                    }
                ],
            ),
            (
                ["pkg:pypi/fetchcode@0.2.0?"],
                [
                    {
                        "valid": True,
                        "exists": True,
                        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                        "purl": "pkg:pypi/fetchcode@0.2.0?",
                    }
                ],
            ),
            (
                ["pkg:pypi/fetchcode@?0.2.0"],
                [
                    {
                        "valid": False,
                        "exists": None,
                        "message": "The provided PackageURL is not valid.",
                        "purl": "pkg:pypi/fetchcode@?0.2.0",
                    }
                ],
            ),
            (
                ["foo"],
                [
                    {
                        "valid": False,
                        "exists": None,
                        "message": "The provided PackageURL is not valid.",
                        "purl": "foo",
                    }
                ],
            ),
        ],
    )
    def test_validate_purl_invalid(self, test_input, expected):
        validated_purls = purlcli.validate_purls(test_input)
        assert validated_purls == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:nginx/nginx@0.8.9?os=windows"],
                [
                    {
                        "valid": True,
                        "exists": None,
                        "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                        "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                    },
                ],
            ),
            (
                [" pkg:nginx/nginx@0.8.9?os=windows"],
                [
                    {
                        "valid": True,
                        "exists": None,
                        "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                        "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                    },
                ],
            ),
            (
                ["pkg:nginx/nginx@0.8.9?os=windows "],
                [
                    {
                        "valid": True,
                        "exists": None,
                        "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                        "purl": "pkg:nginx/nginx@0.8.9?os=windows",
                    }
                ],
            ),
        ],
    )
    def test_validate_purl_strip(self, test_input, expected):
        validated_purls = purlcli.validate_purls(test_input)
        assert validated_purls == expected


# These tests and the underlying code have not yet been converted to a SCTK-like data structure.
class TestPURLCLI_versions(object):
    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                [
                    {
                        "purl": "pkg:pypi/fetchcode",
                        "versions": [
                            {
                                "purl": "pkg:pypi/fetchcode@0.1.0",
                                "version": "0.1.0",
                                "release_date": "2021-08-25T15:15:15.265015+00:00",
                            },
                            {
                                "purl": "pkg:pypi/fetchcode@0.2.0",
                                "version": "0.2.0",
                                "release_date": "2022-09-14T16:36:02.242182+00:00",
                            },
                            {
                                "purl": "pkg:pypi/fetchcode@0.3.0",
                                "version": "0.3.0",
                                "release_date": "2023-12-18T20:49:45.840364+00:00",
                            },
                        ],
                    },
                ],
            ),
            (
                ["pkg:gem/bundler-sass"],
                [
                    {
                        "purl": "pkg:gem/bundler-sass",
                        "versions": [
                            {
                                "purl": "pkg:gem/bundler-sass@0.1.2",
                                "release_date": "2013-12-11T00:27:10.097000+00:00",
                                "version": "0.1.2",
                            },
                        ],
                    },
                ],
            ),
            (
                ["pkg:rubygems/bundler-sass"],
                [],
            ),
            (
                ["pkg:nginx/nginx"],
                [],
            ),
            (
                ["pkg:pypi/zzzzz"],
                [],
            ),
            (
                ["pkg:pypi/?fetchcode"],
                [],
            ),
            (
                ["zzzzz"],
                [],
            ),
        ],
    )
    def test_versions(self, test_input, expected):
        purl_versions = purlcli.list_versions(test_input)
        assert purl_versions == expected

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
                "The provided PackageURL 'pkg:rubygems/bundler-sass' is valid, but `versions` is not supported for this package type.",
            ),
            (
                ["pkg:nginx/nginx"],
                "The provided PackageURL 'pkg:nginx/nginx' is valid, but `versions` is not supported for this package type.",
            ),
            (
                ["pkg:pypi/zzzzz"],
                "There was an error with your 'pkg:pypi/zzzzz' query.  Make sure that 'pkg:pypi/zzzzz' actually exists in the relevant repository.",
            ),
            (
                ["pkg:pypi/?fetchcode"],
                "There was an error with your 'pkg:pypi/?fetchcode' query -- the Package URL you provided is not valid.",
            ),
            (
                ["zzzzz"],
                "There was an error with your 'zzzzz' query -- the Package URL you provided is not valid.",
            ),
        ],
    )
    def test_messages_versions(self, test_input, expected):
        purl_versions = purlcli.check_versions_purl(test_input[0])
        assert purl_versions == expected
