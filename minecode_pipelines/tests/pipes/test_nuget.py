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
from unittest import TestCase

from minecode_pipelines.pipes import nuget
from minecode_pipelines.tests.pipes import TestLogger

TEST_DIR = Path(__file__).parent.parent / "data" / "nuget"


class TestMinecodeNuGetPipe(TestCase):
    def test_collect_package_versions(self):
        page_path = TEST_DIR / "catalog" / "pages" / "page10897.json"
        with page_path.open("r") as f:
            page = json.load(f)

        events = page["items"]
        package_versions = {}
        skipped_package = set()
        nuget.collect_package_versions(
            events=events,
            package_versions=package_versions,
            skipped_packages=skipped_package,
        )
        self.assertEqual(39, len(package_versions))
        self.assertEqual(0, len(skipped_package))

    def test_mine_nuget_package_versions(self):
        logger = TestLogger()

        package_versions, skipped_package = nuget.mine_nuget_package_versions(
            catalog_path=TEST_DIR,
            logger=logger.write,
        )
        self.assertEqual(39, len(package_versions))
        self.assertEqual(0, len(skipped_package))

    def test_get_nuget_purls_from_versions(self):
        packageurls = nuget.get_nuget_purls_from_versions(
            base_purl="pkg:nuget/JetBrains.Platform.Sdk",
            versions={"2.3.1", "1.2.3"},
        )
        self.assertEqual(2, len(packageurls))
        self.assertIn("pkg:nuget/JetBrains.Platform.Sdk@1.2.3", packageurls)
