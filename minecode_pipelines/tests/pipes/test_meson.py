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
        """Test parsing packages from the test releases.json fixture."""
        releases_path = DATA_DIR / "releases.json"
        with open(releases_path, encoding="utf-8") as f:
            releases = json.load(f)

        all_results = []
        for package_name, package_data in releases.items():
            if not package_data:
                continue
            all_results.append(
                get_meson_packages(
                    package_name=package_name,
                    package_data=package_data,
                )
            )

        self.assertEqual(len(all_results), 3)  # ogg, zlib, catch2

        # Check ogg
        ogg_base, ogg_purls = all_results[0]
        self.assertEqual(str(ogg_base), "pkg:meson/ogg")
        self.assertEqual(len(ogg_purls), 4)

        # Check zlib
        zlib_base, zlib_purls = all_results[1]
        self.assertEqual(str(zlib_base), "pkg:meson/zlib")
        self.assertEqual(len(zlib_purls), 3)

        # Check catch2
        catch2_base, catch2_purls = all_results[2]
        self.assertEqual(str(catch2_base), "pkg:meson/catch2")
        self.assertEqual(len(catch2_purls), 2)
        self.assertIn("pkg:meson/catch2@3.5.2-1", catch2_purls)
