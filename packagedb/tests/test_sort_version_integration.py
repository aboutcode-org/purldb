#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.test import TransactionTestCase

from packagedb.models import Package
from packagedb.models import sort_version


class SortVersionIntegrationTestCase(TransactionTestCase):
    """Integration tests for sort_version with real-world PURL data."""

    def tearDown(self):
        Package.objects.all().delete()

    def _test_ecosystem_sorting(self, pkg_type, versions_unordered, expected_ordered, **kwargs):
        """Test version sorting for any ecosystem."""
        packages = [
            Package.objects.create(
                download_url=f"http://{pkg_type}-{hash(version)}.com",
                type=pkg_type,
                version=version,
                **kwargs,
            )
            for version in versions_unordered
        ]
        sorted_versions = [p.version for p in sort_version(packages)]
        self.assertEqual(expected_ordered, sorted_versions)

    def test_ecosystem_versions(self):
        """Test version sorting for multiple real-world ecosystems."""
        test_cases = [
            (
                "npm",
                ["4.17.21", "4.17.20", "4.17.10", "4.17.4", "4.16.6", "4.0.0", "3.10.1", "1.3.1"],
                ["1.3.1", "3.10.1", "4.0.0", "4.16.6", "4.17.4", "4.17.10", "4.17.20", "4.17.21"],
                {"name": "lodash"},
            ),
            (
                "pypi",
                ["4.1", "4.1rc1", "4.1b1", "4.1a1", "4.0.8", "4.0", "3.2.16", "2.1.15"],
                ["2.1.15", "3.2.16", "4.0", "4.0.8", "4.1a1", "4.1b1", "4.1rc1", "4.1"],
                {"name": "django"},
            ),
            (
                "maven",
                ["4.13.2", "4.13", "4.10", "4.8.2", "4.5", "3.8.2", "3.8.1"],
                ["3.8.1", "3.8.2", "4.5", "4.8.2", "4.10", "4.13", "4.13.2"],
                {"namespace": "junit", "name": "junit"},
            ),
            (
                "gem",
                ["7.0.4", "7.0.3.1", "6.1.6.1", "6.0.6", "5.2.8.1", "5.2.0"],
                ["5.2.0", "5.2.8.1", "6.0.6", "6.1.6.1", "7.0.3.1", "7.0.4"],
                {"name": "rails"},
            ),
            (
                "nuget",
                ["13.0.1", "12.0.3", "10.0.3", "9.0.1", "8.0.3", "6.0.8"],
                ["6.0.8", "8.0.3", "9.0.1", "10.0.3", "12.0.3", "13.0.1"],
                {"name": "Newtonsoft.Json"},
            ),
            (
                "cargo",
                ["1.0.147", "1.0.100", "1.0.10", "1.0.0", "0.9.15", "0.9.0"],
                ["0.9.0", "0.9.15", "1.0.0", "1.0.10", "1.0.100", "1.0.147"],
                {"name": "serde"},
            ),
            (
                "deb",
                ["2.31-13+deb11u5", "2.31-13", "2.28-10", "2.27-3ubuntu1", "2.24-11+deb9u4"],
                ["2.24-11+deb9u4", "2.27-3ubuntu1", "2.28-10", "2.31-13", "2.31-13+deb11u5"],
                {"name": "libc6"},
            ),
            (
                "golang",
                ["v1.8.1", "v1.7.0", "v1.5.0", "v1.2.0", "v1.0.0", "v0.9.0"],
                ["v0.9.0", "v1.0.0", "v1.2.0", "v1.5.0", "v1.7.0", "v1.8.1"],
                {"namespace": "github.com/pkg", "name": "errors"},
            ),
        ]
        for pkg_type, unsorted, expected, kwargs in test_cases:
            with self.subTest(pkg_type=pkg_type):
                self._test_ecosystem_sorting(pkg_type, unsorted, expected, **kwargs)

    def test_swift_with_git_tag_suffix(self):
        """
        Test Swift packages with Git tag suffixes (issue #808).

        Swift is unsupported by univers, so uses natsort fallback.
        Versions with ^{} suffix should come after their base versions.
        """
        versions = ["5.6.4", "5.6.4^{}", "5.4.4", "5.4.4^{}", "5.2.2", "5.2.2^{}", "4.8.2"]
        packages = [
            Package.objects.create(
                download_url=f"http://swift-{i}.com",
                type="swift",
                name="Alamofire",
                version=version,
            )
            for i, version in enumerate(versions)
        ]
        sorted_versions = [p.version for p in sort_version(packages)]

        # Base versions should come before their ^{} suffixed versions
        self.assertLess(sorted_versions.index("5.2.2"), sorted_versions.index("5.2.2^{}"))
        self.assertLess(sorted_versions.index("5.4.4"), sorted_versions.index("5.4.4^{}"))

    def test_cross_ecosystem_latest_version(self):
        """Test get_latest_version across different ecosystems."""
        # npm
        npm_pkgs = [
            Package.objects.create(
                download_url=f"http://npm-{i}.com", type="npm", name="test", version=v
            )
            for i, v in enumerate(["1.0.0", "1.10.0", "1.2.0"])
        ]
        self.assertEqual(npm_pkgs[1], npm_pkgs[0].get_latest_version())

        # pypi
        pypi_pkgs = [
            Package.objects.create(
                download_url=f"http://pypi-{i}.com", type="pypi", name="pkg", version=v
            )
            for i, v in enumerate(["2.0", "2.0.1", "2.0a1"])
        ]
        self.assertEqual(pypi_pkgs[1], pypi_pkgs[0].get_latest_version())
