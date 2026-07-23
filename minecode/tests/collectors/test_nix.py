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

from django.test import TestCase as DjangoTestCase

from packageurl import PackageURL
from unittest import mock

import packagedb
from minecode.collectors import nix
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class NixPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.expected_json_loc = self.get_test_loc("nix/SDL_mixer_package-expected.json")
        with open(self.expected_json_loc) as f:
            self.expected_json_contents = json.load(f)
        """
        self.scan_package = NpmPackageJsonHandler._parse(
            json_data=self.expected_json_contents,
        )
        """

    @mock.patch("minecode.collectors.nix.fetch_json_response")
    @mock.patch("minecode.collectors.nix.verify_url_existence")
    def test_get_nix_package_data(self, mock_verify, mock_fetch, regen=FIXTURES_REGEN):
        mock_verify.return_value = True
        mock_fetch.return_value = self.expected_json_contents
        purl = PackageURL.from_string("pkg:nix/nixpkgs/SDL_mixer@1.2.12")
        json_contents = nix.get_nix_package_data(purl)
        if regen:
            with open(self.expected_json_loc, "w") as f:
                json.dump(json_contents, f, indent=3, separators=(",", ":"))
        self.assertEqual(self.expected_json_contents, json_contents)

    def test_parse_license(self):
        license_data = {
            "deprecated": "false",
            "free": "true",
            "fullName": 'BSD 3-clause "New" or "Revised" License',
            "licenseType": "simple",
            "redistributable": "true",
            "shortName": "bsd3",
            "spdxId": "BSD-3-Clause",
            "url": "https://spdx.org/licenses/BSD-3-Clause.html",
        }
        result = nix.parse_license(license_data)
        self.assertEqual("BSD-3-Clause", result)

    @mock.patch("minecode.collectors.nix.subprocess.run")
    def test_get_nix_package_data_via_cli(self, mock_run):
        mock_cli_output = {
            "description": "Scientific tools for Python",
            "homepage": "https://numpy.org/",
            "license": {"spdxId": "BSD-3-Clause"},
            "version": "2.4.4",
            "system": "x86_64-linux",
            "outputs": {
                "dist": "/nix/store/3wmy167jrryy19h6i6hnfbzy4j0ndkma-python3.13-numpy-2.4.4-dist",
                "out": "/nix/store/l59n6vzkswz23y6s4pr6cmv2p4dpd5f0-python3.13-numpy-2.4.4",
            },
        }
        mock_run.return_value.stdout = json.dumps(mock_cli_output)

        metadata = {
            "summary": "Scientific tools for Python",
            "homepage_url": "https://numpy.org/",
            "license": "BSD-3-Clause",
            "releases": [
                {
                    "version": "2.4.4",
                    "platforms": [
                        {
                            "system": "x86_64-linux",
                            "outputs": [
                                {
                                    "name": "dist",
                                    "path": "/nix/store/3wmy167jrryy19h6i6hnfbzy4j0ndkma-python3.13-numpy-2.4.4-dist",
                                },
                                {
                                    "name": "out",
                                    "path": "/nix/store/l59n6vzkswz23y6s4pr6cmv2p4dpd5f0-python3.13-numpy-2.4.4",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        result = nix.get_nix_package_data_via_cli(
            PackageURL.from_string("pkg:nix/nixpkgs/python3Packages.numpy@2.4.4")
        )
        self.assertEqual(metadata, result)

    @mock.patch("minecode.collectors.nix.fetch_json_response")
    @mock.patch("minecode.collectors.nix.verify_url_existence")
    def test_map_nix_package(self, mock_verify, mock_fetch):
        mock_verify.return_value = True
        mock_fetch.return_value = self.expected_json_contents

        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string("pkg:nix/nixpkgs/SDL_mixer@1.2.12")
        nix.map_nix_package(package_url, ("test_pipeline"))
        package_count = packagedb.models.Package.objects.all().count()
        # There are 4 different systems and each system has 2 outputs, so
        # we expect 8 packages to be created in total.
        self.assertEqual(8, package_count)
        # package = packagedb.models.Package.objects.all().first()
        packages = packagedb.models.Package.objects.all()

        expected_purl_data = [
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=out&system=aarch64-linux",
                "https://cache.nixos.org/nar/07q6kl7ndvxi550gk7wm8j7m3lhbfbl5pshgx0amx38p4pq4haml.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=dev&system=aarch64-linux",
                "https://cache.nixos.org/nar/13vh3dfwp5bcy75csf6l69zyxa8y9w0azy8drx9nacdqq84jzhl1.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=out&system=aarch64-darwin",
                "https://cache.nixos.org/nar/10iscj2cnh5yhdgc5rnb9rmzr5galwmzmar495c9k410k7afc2kw.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=dev&system=aarch64-darwin",
                "https://cache.nixos.org/nar/11zwp2lzw481agxqgg7f8ikj4zbivl7a2r0nvwsr107c963f59pl.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=out&system=x86_64-darwin",
                "https://cache.nixos.org/nar/1y793cshy2hvdch0g3svi8bg0jlnx96jxsyi7960c1272cq7ricf.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=dev&system=x86_64-darwin",
                "https://cache.nixos.org/nar/115jv555r5lnkgb2hp9p8qz31h5s1a4sgjdkbaf0cp9ccb6lvl4y.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=out&system=x86_64-linux",
                "https://cache.nixos.org/nar/0phnvv0k4bnfb4mnjhldh4rksqy2pxsg53n6nh8zd7ikixq4q2qi.nar.zst",
            ),
            (
                "pkg:nix/nixpkgs/SDL_mixer@1.2.12?commit=3d46470bb3030020f7e1361f33514854f5bfa86d&output=dev&system=x86_64-linux",
                "https://cache.nixos.org/nar/1m1jh8jg98i0czg5hdiaa9yjmz48f0ldx8vwr2hbmlz65pcmrlls.nar.zst",
            ),
        ]

        self.assertEqual(len(packages), len(expected_purl_data))

        for package, (expected_purl, expected_url) in zip(packages, expected_purl_data):
            self.assertEqual(expected_purl, package.purl)
            self.assertEqual(expected_url, package.download_url)
