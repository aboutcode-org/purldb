#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
from pathlib import Path

from django.test import TestCase

from minecode_pipelines.pipes.meson import get_meson_packages

DATA_DIR = Path(__file__).parent.parent / "test_data" / "meson"


class MesonPipeTests(TestCase):
    def test_get_meson_packages_empty_versions(self):
        """Test that get_meson_packages handles empty version lists."""
        package_data = {
            "dependency_names": ["empty-pkg"],
            "versions": [],
        }
        base_purl, versioned_purls = get_meson_packages("empty-pkg", package_data)

        self.assertEqual(str(base_purl), "pkg:meson/empty-pkg")
        self.assertEqual(versioned_purls, [])

    def test_get_meson_packages_no_versions_key(self):
        """Test that get_meson_packages handles missing versions key."""
        package_data = {
            "dependency_names": ["no-ver"],
        }
        base_purl, versioned_purls = get_meson_packages("no-ver", package_data)

        self.assertEqual(str(base_purl), "pkg:meson/no-ver")
        self.assertEqual(versioned_purls, [])

    def test_get_meson_packages_from_releases_json(self):
        """Test parsing packages from the real WrapDB releases.json fixture
        using data-driven expected output."""
        releases_path = DATA_DIR / "releases.json"
        expected_path = DATA_DIR / "expected_purls.json"

        with open(releases_path, encoding="utf-8") as f:
            releases = json.load(f)

        with open(expected_path, encoding="utf-8") as f:
            expected = json.load(f)

        actual = {}
        for package_name, package_data in releases.items():
            if not package_data:
                continue
            base_purl, versioned_purls = get_meson_packages(
                package_name=package_name,
                package_data=package_data,
            )
            actual[str(base_purl)] = sorted(versioned_purls)

        self.assertEqual(actual, expected)
