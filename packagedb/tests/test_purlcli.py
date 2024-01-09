import json
import os

from click.testing import CliRunner
from commoncode.testcase import FileBasedTesting
from django.test import TestCase
from fetchcode.package_versions import PackageVersion, router, versions

import purlcli
from packagedb.models import Package


class TestPURLCLI(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), "data")

    # QUESTION: These four validate tests call validate_purls(), which queries the validate endpoint.  Is that what we want here?  I think we might be able to mock the API if we pass the API to the validate_purls() function instead of defining the API inside the function as we do now.

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

    # def test_versions(self):
    #     purls = ["pkg:pypi/fetchcode"]
    #     abc = purlcli.list_versions(purls)
    #     print(f"\nabc = {abc}")

    #     for purl_list in abc:
    #         for p in purl_list:
    #             # print(PackageVersion.to_dict(p))
    #             p_dict = PackageVersion.to_dict(p)
    #             print(f"\np_dict = {p_dict}")
    #             print(f"\ntype(p_dict) = {type(p_dict)}")

    #             json_p_dict = json.dumps(p_dict)
    #             print(f"\njson_p_dict = {json_p_dict}")
    #             print(f"\ntype(json_p_dict) = {type(json_p_dict)}")


# 2024-01-08 Monday 17:55:15.  Based on test_api.py's class PurlValidateApiTestCase(TestCase).
class TestPURLCLI_API(TestCase):
    def setUp(self):
        self.package_data = {
            "type": "npm",
            "namespace": "",
            "name": "foobar",
            "version": "1,1.0",
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

    def test_api_purl_validation(self):
        data1 = {
            # "purl": "pkg:npm/foobar@1.1.0",
            "purl": "pkg:pypi/packagedb@2.0.0",
            "check_existence": True,
        }
        response1 = self.client.get(f"/api/validate/", data=data1)

        print(f"\nresponse1 = {response1}")
        print(f"\nresponse1.data = {response1.data}")
        print(f"")

        data2 = {
            # "purl": "pkg:npm/?foobar@1.1.0",
            "purl": "pkg:pypi/?packagedb@2.0.0",
            "check_existence": True,
        }
        response2 = self.client.get(f"/api/validate/", data=data2)

        print(f"\nresponse2 = {response2}")
        print(f"\nresponse2.data = {response2.data}")
        print(f"")

        self.assertEqual(True, response1.data["valid"])
        self.assertEqual(True, response1.data["exists"])
        self.assertEqual(
            "The provided Package URL is valid, and the package exists in the upstream repo.",
            response1.data["message"],
        )

        self.assertEqual(False, response2.data["valid"])
        self.assertEqual(
            "The provided PackageURL is not valid.", response2.data["message"]
        )

        # ZZZ: 2024-01-08 Monday 18:54:51.  Some exploring:

        data3 = {
            # "purl": "pkg:npm/ogdendunes",
            # "purl": "pkg:pypi/ogdendunes",
            "purl": "pkg:pypi/zzzzz@2.0.0",
            "check_existence": True,
        }
        response3 = self.client.get(f"/api/validate/", data=data3)

        print(f"\nresponse3 = {response3}")
        print(f"\nresponse3.data = {response3.data}")
        print(f"")

        self.assertEqual(True, response3.data["valid"])
        self.assertEqual(False, response3.data["exists"])
        self.assertEqual(
            "The provided PackageURL is valid but does not exist in the upstream repo.",
            response3.data["message"],
        )

        data4 = {
            # "purl": "pkg:nginx/nginx@0.8.9?os=windows",
            "purl": "pkg:nginx/nginx@0.8.9",
            "check_existence": True,
        }
        response4 = self.client.get(f"/api/validate/", data=data4)

        print(f"\nresponse4 = {response4}")
        print(f"\nresponse4.data = {response4.data}")
        print(f"")

        self.assertEqual(True, response4.data["valid"])
        self.assertEqual(False, response4.data["exists"])
        self.assertEqual(
            "The provided PackageURL is valid but does not exist in the upstream repo.",
            response4.data["message"],
        )
