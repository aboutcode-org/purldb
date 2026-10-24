#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest import mock

from minecode.pipes import INITIAL_SYNC_STATE
from minecode.pipes import npm


class TestMinecodeNpmPipe(TestCase):
    def test_get_npm_base_purl(self):
        self.assertEqual("pkg:npm/lodash", npm.get_npm_base_purl("lodash"))
        self.assertEqual("pkg:npm/%40babel/core", npm.get_npm_base_purl("@babel/core"))

    def test_get_npm_packages_to_sync_skips_already_mined_packages(self):
        names = ["lodash", "@babel/core", "express", "react"]
        with tempfile.TemporaryDirectory() as tmpdir:
            packages_file = Path(tmpdir) / "packages.json"
            packages_file.write_text(json.dumps({"packages": names}))

            with mock.patch.object(
                npm,
                "get_mined_packages_from_checkpoint",
                return_value=["pkg:npm/lodash", "pkg:npm/%40babel/core"],
            ):
                packages_to_sync, synced = npm.get_npm_packages_to_sync(
                    packages_file=str(packages_file),
                    state=INITIAL_SYNC_STATE,
                )

        self.assertEqual(["express", "react"], sorted(packages_to_sync))
        self.assertEqual(["pkg:npm/lodash", "pkg:npm/%40babel/core"], synced)
