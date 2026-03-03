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
EXPECTED_PATH = DATA_DIR / "expected_purls.json"


class MesonPipeTests(TestCase):
    def test_get_meson_packages_basic(self):
        """Test that get_meson_packages correctly parses a single package entry."""
        package_data = {
            "dependency_names": ["ogg"],
            "versions": ["1.3.6-1", "1.3.5-3", "1.3.5-2", "1.3.5-1"],
        }
        base_purl, versioned_purls = get_meson_packages("ogg", package_data)

        self.assertEqual(str(base_purl), "pkg:meson/ogg")
        self.assertEqual(len(versioned_purls), 4)
        self.assertIn("pkg:meson/ogg@1.3.6-1", versioned_purls)
        self.assertIn("pkg:meson/ogg@1.3.5-1", versioned_purls)

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
        """Test parsing packages from the test releases.json fixture with data-driven expected output."""
        releases_path = DATA_DIR / "releases.json"
        with open(releases_path, encoding="utf-8") as f:
            releases = json.load(f)

        actual = {}
        for package_name, package_data in releases.items():
            if not package_data:
                continue
            base_purl, versioned_purls = get_meson_packages(
                package_name=package_name,
                package_data=package_data,
            )
            actual[str(base_purl)] = sorted(versioned_purls)

        with open(EXPECTED_PATH, encoding="utf-8") as ef:
            expected = json.load(ef)
        filtered_actual = {k: actual[k] for k in expected.keys()}
        self.assertEqual(filtered_actual, expected)
