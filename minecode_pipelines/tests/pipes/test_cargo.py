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
from unittest import mock
from unittest.mock import Mock, patch
import saneyaml
from django.test import TestCase

from minecode_pipelines.pipes import write_data_to_yaml_file
from minecode_pipelines.pipes.cargo import store_cargo_packages

DATA_DIR = Path(__file__).parent.parent / "test_data" / "cargo"


class CargoPipelineTests(TestCase):
    @patch("minecode_pipelines.pipes.cargo.write_data_to_yaml_file")
    def test_collect_packages_from_cargo_calls_write(self, mock_write):
        packages_file = DATA_DIR / "c5store"
        expected_file = DATA_DIR / "c5store-expected.yaml"

        packages = []
        with open(packages_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    packages.append(json.loads(line))

        with open(expected_file, encoding="utf-8") as f:
            expected = saneyaml.load(f)

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Mock()
            repo.working_dir = tmpdir

            store_cargo_packages(packages, repo)

            mock_write.assert_called_once()
            args, kwargs = mock_write.call_args
            base_purl, written_packages = kwargs["path"], kwargs["data"]

            expected_base_purl = (
                Path(tmpdir) / "aboutcode-packages-cargo-0" / "cargo" / "c5store" / "purls.yml"
            )

            self.assertEqual(str(base_purl), str(expected_base_purl))
            self.assertEqual(written_packages, expected)

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
        self._assert_purls_written(
            [{"purl": "pkg:pypi/django@4.2.0"}, {"purl": "pkg:pypi/django@4.3.0"}]
        )

    def test_add_empty_purl_result_with_mock_repo(self):
        self._assert_purls_written([])

    def test_add_invalid_purl_with_mock_repo(self):
        # invalid but still written as empty file
        self._assert_purls_written([{"purl": "pkg:pypi/django"}])
