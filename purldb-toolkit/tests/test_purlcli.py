import pytest
from purldb_toolkit import purlcli


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


class TestPURLCLI_meta(object):
    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                ["pkg:pypi/fetchcode"],
                [
                    {
                        "purl": "pkg:pypi/fetchcode",
                        "metadata": [
                            {
                                "type": "pypi",
                                "namespace": None,
                                "name": "fetchcode",
                                "version": None,
                                "qualifiers": {},
                                "subpath": None,
                                "primary_language": None,
                                "description": None,
                                "release_date": None,
                                "parties": [],
                                "keywords": [],
                                "homepage_url": "https://github.com/nexB/fetchcode",
                                "download_url": None,
                                "api_url": "https://pypi.org/pypi/fetchcode/json",
                                "size": None,
                                "sha1": None,
                                "md5": None,
                                "sha256": None,
                                "sha512": None,
                                "bug_tracking_url": None,
                                "code_view_url": None,
                                "vcs_url": None,
                                "copyright": None,
                                "license_expression": None,
                                "declared_license": "Apache-2.0",
                                "notice_text": None,
                                "root_path": None,
                                "dependencies": [],
                                "contains_source_code": None,
                                "source_packages": [],
                                "purl": "pkg:pypi/fetchcode",
                                "repository_homepage_url": None,
                                "repository_download_url": None,
                                "api_data_url": None,
                            },
                            {
                                "type": "pypi",
                                "namespace": None,
                                "name": "fetchcode",
                                "version": "0.1.0",
                                "qualifiers": {},
                                "subpath": None,
                                "primary_language": None,
                                "description": None,
                                "release_date": None,
                                "parties": [],
                                "keywords": [],
                                "homepage_url": "https://github.com/nexB/fetchcode",
                                "download_url": "https://files.pythonhosted.org/packages/19/a0/c90e5ba4d71ea1a1a89784f6d839ffb0dbf32d270cba04d5602188cb3713/fetchcode-0.1.0-py3-none-any.whl",
                                "api_url": "https://pypi.org/pypi/fetchcode/json",
                                "size": None,
                                "sha1": None,
                                "md5": None,
                                "sha256": None,
                                "sha512": None,
                                "bug_tracking_url": None,
                                "code_view_url": None,
                                "vcs_url": None,
                                "copyright": None,
                                "license_expression": None,
                                "declared_license": "Apache-2.0",
                                "notice_text": None,
                                "root_path": None,
                                "dependencies": [],
                                "contains_source_code": None,
                                "source_packages": [],
                                "purl": "pkg:pypi/fetchcode@0.1.0",
                                "repository_homepage_url": None,
                                "repository_download_url": None,
                                "api_data_url": None,
                            },
                            {
                                "type": "pypi",
                                "namespace": None,
                                "name": "fetchcode",
                                "version": "0.2.0",
                                "qualifiers": {},
                                "subpath": None,
                                "primary_language": None,
                                "description": None,
                                "release_date": None,
                                "parties": [],
                                "keywords": [],
                                "homepage_url": "https://github.com/nexB/fetchcode",
                                "download_url": "https://files.pythonhosted.org/packages/d7/e9/96e9302e84e326b3c10a40c1723f21f4db96b557a17c6871e7a4c6336906/fetchcode-0.2.0-py3-none-any.whl",
                                "api_url": "https://pypi.org/pypi/fetchcode/json",
                                "size": None,
                                "sha1": None,
                                "md5": None,
                                "sha256": None,
                                "sha512": None,
                                "bug_tracking_url": None,
                                "code_view_url": None,
                                "vcs_url": None,
                                "copyright": None,
                                "license_expression": None,
                                "declared_license": "Apache-2.0",
                                "notice_text": None,
                                "root_path": None,
                                "dependencies": [],
                                "contains_source_code": None,
                                "source_packages": [],
                                "purl": "pkg:pypi/fetchcode@0.2.0",
                                "repository_homepage_url": None,
                                "repository_download_url": None,
                                "api_data_url": None,
                            },
                            {
                                "type": "pypi",
                                "namespace": None,
                                "name": "fetchcode",
                                "version": "0.3.0",
                                "qualifiers": {},
                                "subpath": None,
                                "primary_language": None,
                                "description": None,
                                "release_date": None,
                                "parties": [],
                                "keywords": [],
                                "homepage_url": "https://github.com/nexB/fetchcode",
                                "download_url": "https://files.pythonhosted.org/packages/8d/fb/e45da0abf63504c3f88ad02537dc9dc64ea5206b09ce29cfb8191420d678/fetchcode-0.3.0-py3-none-any.whl",
                                "api_url": "https://pypi.org/pypi/fetchcode/json",
                                "size": None,
                                "sha1": None,
                                "md5": None,
                                "sha256": None,
                                "sha512": None,
                                "bug_tracking_url": None,
                                "code_view_url": None,
                                "vcs_url": None,
                                "copyright": None,
                                "license_expression": None,
                                "declared_license": "Apache-2.0",
                                "notice_text": None,
                                "root_path": None,
                                "dependencies": [],
                                "contains_source_code": None,
                                "source_packages": [],
                                "purl": "pkg:pypi/fetchcode@0.3.0",
                                "repository_homepage_url": None,
                                "repository_download_url": None,
                                "api_data_url": None,
                            },
                        ],
                    }
                ],
            ),
            (
                ["pkg:gem/bundler-sass"],
                [],
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
    def test_meta_details(self, test_input, expected):
        purl_meta = purlcli.get_meta_details(test_input)
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
