import json
import os

from commoncode.testcase import FileBasedTesting
from django.test import TestCase

import purlcli
from packagedb.models import Package


class TestPURLCLI_validate(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), "data")

    def test_validate_purl(self):
        test_purls = [
            "pkg:pypi/fetchcode@0.2.0",
            "pkg:pypi/fetchcode@10.2.0",
            "pkg:nginx/nginx@0.8.9?os=windows",
            "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
        ]
        validated_purls = purlcli.validate_purls(test_purls)

        expected_results = [
            {
                "valid": True,
                "exists": True,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
                "purl": "pkg:pypi/fetchcode@0.2.0",
            },
            {
                "valid": True,
                "exists": False,
                "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
                "purl": "pkg:pypi/fetchcode@10.2.0",
            },
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


class TestPURLCLI_versions(FileBasedTesting):
    # TODO: can we test the terminal warnings, e.g., `There was an error with your 'zzzzz' query -- the Package URL you provided is not valid.`?
    def test_versions(self):
        purls1 = ["pkg:pypi/fetchcode"]
        purls2 = ["pkg:pypi/zzzzz"]
        purls3 = ["zzzzz"]
        purl_versions1 = purlcli.list_versions(purls1)
        purl_versions2 = purlcli.list_versions(purls2)
        purl_versions3 = purlcli.list_versions(purls3)

        expected_results1 = [
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
        ]
        expected_results2 = []
        expected_results3 = []

        self.assertEqual(purl_versions1, expected_results1)
        self.assertEqual(purl_versions2, expected_results2)
        self.assertEqual(purl_versions3, expected_results3)


class TestPURLAPI_validate(TestCase):
    def setUp(self):
        self.package_data = {
            "type": "npm",
            "namespace": "",
            "name": "nosuchpackage",
            "version": "1.1.0",
            "qualifiers": "",
            "subpath": "",
            "download_url": "",
            "filename": "Foo.zip",
            "sha1": "testsha1",
            "md5": "testmd5",
            "size": 101,
        }
        self.package = Package.objects.create(**self.package_data)
        self.package.refresh_from_db()

    def test_api_validate_purl(self):
        data1 = {
            "purl": "pkg:pypi/packagedb@2.0.0",
            "check_existence": True,
        }
        response1 = self.client.get(f"/api/validate/", data=data1)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(True, response1.data["valid"])
        self.assertEqual(True, response1.data["exists"])
        self.assertEqual(
            "The provided Package URL is valid, and the package exists in the upstream repo.",
            response1.data["message"],
        )

        data2 = {
            "purl": "pkg:pypi/?packagedb@2.0.0",
            "check_existence": True,
        }
        response2 = self.client.get(f"/api/validate/", data=data2)

        self.assertEqual(response2.status_code, 200)
        self.assertEqual(False, response2.data["valid"])
        self.assertEqual(None, response2.data["exists"])
        self.assertEqual(
            "The provided PackageURL is not valid.", response2.data["message"]
        )

        data3 = {
            "purl": "pkg:pypi/zzzzz@2.0.0",
            "check_existence": True,
        }
        response3 = self.client.get(f"/api/validate/", data=data3)

        self.assertEqual(response3.status_code, 200)
        self.assertEqual(True, response3.data["valid"])
        self.assertEqual(False, response3.data["exists"])
        self.assertEqual(
            "The provided PackageURL is valid, but does not exist in the upstream repo.",
            response3.data["message"],
        )

        data4 = {
            "purl": "pkg:nginx/nginx@0.8.9",
            "check_existence": True,
        }
        response4 = self.client.get(f"/api/validate/", data=data4)

        self.assertEqual(response4.status_code, 200)
        self.assertEqual(True, response4.data["valid"])
        self.assertEqual(None, response4.data["exists"])
        self.assertEqual(
            "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
            response4.data["message"],
        )

        data5 = {
            "purl": "pkg:npm/nosuchpackage@1.1.0",
            "check_existence": True,
        }
        response5 = self.client.get(f"/api/validate/", data=data5)

        self.assertEqual(response5.status_code, 200)
        self.assertEqual(True, response5.data["valid"])
        self.assertEqual(True, response5.data["exists"])
        self.assertEqual(
            "The provided Package URL is valid, and the package exists in the upstream repo.",
            response5.data["message"],
        )

        data6 = {
            "purl": "pkg:npm/nosuchpackage@1.1.1",
            "check_existence": True,
        }
        response6 = self.client.get(f"/api/validate/", data=data6)

        self.assertEqual(response6.status_code, 200)
        self.assertEqual(True, response6.data["valid"])
        self.assertEqual(False, response6.data["exists"])
        self.assertEqual(
            "The provided PackageURL is valid, but does not exist in the upstream repo.",
            response6.data["message"],
        )
