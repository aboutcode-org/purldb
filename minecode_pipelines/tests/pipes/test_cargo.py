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

import saneyaml
from unittest import TestCase

from minecode_pipelines.pipes.cargo import get_cargo_packages

DATA_DIR = Path(__file__).parent.parent / "test_data" / "cargo"


class CargoPipelineTests(TestCase):
    def test_collect_packages_from_cargo_calls_write(self):
        packages_file = DATA_DIR / "c5store"
        expected_file = DATA_DIR / "c5store-expected.yaml"

        packages = []
        with open(packages_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    packages.append(json.loads(line))

        with open(expected_file, encoding="utf-8") as f:
            expected = saneyaml.load(f)

        base, purls = get_cargo_packages(packages)

        self.assertEqual(str(base), "pkg:cargo/c5store")
        self.assertEqual(purls, expected)
