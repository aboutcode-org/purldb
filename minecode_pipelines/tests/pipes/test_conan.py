#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import tempfile
from pathlib import Path
from unittest import mock
import saneyaml
import yaml

from django.test import TestCase

from minecode_pipelines.pipes import write_data_to_yaml_file
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

    def _assert_purls_written(self, purls):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            mock_repo = mock.MagicMock()
            mock_repo.working_dir = str(repo_dir)
            mock_repo.index.add = mock.MagicMock()

            purls_file = repo_dir / "purls.yaml"

            write_data_to_yaml_file(purls_file, purls)

            self.assertTrue(purls_file.exists())

            with open(purls_file, encoding="utf-8") as f:
                content = saneyaml.load(f)

            self.assertEqual(content, purls)

    def test_add_purl_result_with_mock_repo(self):
        purls = [
            {"purl": "pkg:conan/cairo@1.18.0"},
            {"purl": "pkg:conan/cairo@1.17.8"},
            {"purl": "pkg:conan/cairo@1.17.6"},
            {"purl": "pkg:conan/cairo@1.17.4"},
        ]

        self._assert_purls_written(purls)

    def test_add_empty_purl_result_with_mock_repo(self):
        self._assert_purls_written([])
