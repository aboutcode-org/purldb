#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
import saneyaml
import yaml

from django.test import TestCase

from minecode_pipelines.pipes.conan import get_conan_packages

DATA_DIR = Path(__file__).parent.parent / "test_data" / "conan"


class ConanPipelineTests(TestCase):
    def test_collect_packages_from_conan_calls_write(self, mock_write):
        packages_file = DATA_DIR / "cairo-config.yml"
        expected_file = DATA_DIR / "expected-cairo-purls.yml"

        with open(packages_file, encoding="utf-8") as f:
            versions_data = yaml.safe_load(f)

        with open(expected_file, encoding="utf-8") as f:
            expected = saneyaml.load(f)

        base, purls = get_conan_packages("cairo", versions_data)
        self.assertEqual(purls, expected)
        self.assertEqual(str(base), "pkg:cargo/c5store")
