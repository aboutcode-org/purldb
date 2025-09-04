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
from unittest.mock import Mock, patch
import saneyaml
import yaml

from django.test import TestCase
from packageurl import PackageURL

from minecode_pipelines.pipes.conan import add_purl_result, collect_and_write_purls_for_canon

DATA_DIR = Path(__file__).parent.parent / "test_data" / "conan"


class ConanPipelineTests(TestCase):
    def _get_temp_dir(self):
        import tempfile

        return tempfile.mkdtemp()

    @patch("minecode_pipelines.pipes.conan.write_purls_to_repo")
    def test_collect_packages_from_cargo_calls_write(self, mock_write):
        packages_file = DATA_DIR / "cairo-config.yml"
        expected_file = DATA_DIR / "expected-cairo-purls.yml"

        with open(packages_file, encoding="utf-8") as f:
            versions_data = yaml.safe_load(f)

        with open(expected_file, encoding="utf-8") as f:
            expected = saneyaml.load(f)

        repo = Mock()

        pacakge_name = "cairo"
        result = collect_and_write_purls_for_canon(pacakge_name, versions_data, repo)
        self.assertIsNone(result)

        mock_write.assert_called_once()
        args, kwargs = mock_write.call_args
        called_repo, base_purl, written_packages, push_commit = args

        self.assertEqual(called_repo, repo)

        expected_base_purl = PackageURL(
            type="conan",
            name="cairo",
        )

        self.assertEqual(str(base_purl), str(expected_base_purl))
        self.assertEqual(written_packages, expected)

    def test_add_purl_result_with_mock_repo(self):
        purls = [
            {"purl": "pkg:conan/cairo@1.18.0"},
            {"purl": "pkg:conan/cairo@1.17.8"},
            {"purl": "pkg:conan/cairo@1.17.6"},
            {"purl": "pkg:conan/cairo@1.17.4"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            mock_repo = mock.MagicMock()
            mock_repo.working_dir = str(repo_dir)
            mock_repo.index.add = mock.MagicMock()

            purls_file = repo_dir / "purls.yaml"

            relative_path = add_purl_result(purls, mock_repo, purls_file)

            written_file = repo_dir / relative_path
            self.assertTrue(written_file.exists())

            with open(written_file, encoding="utf-8") as f:
                content = saneyaml.load(f)

            self.assertEqual(content, purls)

            mock_repo.index.add.assert_called_once_with([relative_path])
