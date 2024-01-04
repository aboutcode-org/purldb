import os

from click.testing import CliRunner
from commoncode.testcase import FileBasedTesting

import purlcli


class TestPURLCLI(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), "data")

    def test_validate_purl(self):
        test_purls = [
            "pkg:nginx/nginx@0.8.9?os=windows",
            "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
        ]

        validated_purls = purlcli.validate_purls(test_purls)

        expected_results = [
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx@0.8.9?os=windows",
            },
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
            },
        ]

        self.assertEqual(validated_purls, expected_results)

    def test_validate_purl_empty(self):
        test_purls = []

        validated_purls = purlcli.validate_purls(test_purls)

        expected_results = []

        self.assertEqual(validated_purls, expected_results)

    def test_validate_purl_invalid(self):
        test_purls = [
            "foo",
        ]

        validated_purls = purlcli.validate_purls(test_purls)

        expected_results = [
            {
                "valid": False,
                "exists": None,
                "message": "The provided PackageURL is not valid.",
                "purl": "foo",
            }
        ]

        self.assertEqual(validated_purls, expected_results)

    def test_validate_purl_strip(self):
        test_purls = [
            "pkg:nginx/nginx@0.8.9?os=windows",
            " pkg:nginx/nginx@0.8.9?os=windows",
            "pkg:nginx/nginx@0.8.9?os=windows ",
        ]

        validated_purls = purlcli.validate_purls(test_purls)

        expected_results = [
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx@0.8.9?os=windows",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx@0.8.9?os=windows",
            },
            {
                "valid": True,
                "exists": None,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
                "purl": "pkg:nginx/nginx@0.8.9?os=windows",
            },
        ]

        self.assertEqual(validated_purls, expected_results)
