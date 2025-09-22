import json
import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import Mock, patch
import saneyaml
from django.test import TestCase

from minecode_pipelines.miners import write_packageurls_to_file
from minecode_pipelines.pipes.cargo import store_cargo_packages

DATA_DIR = Path(__file__).parent.parent / "test_data" / "cargo"


class CargoPipelineTests(TestCase):
    @patch("minecode_pipelines.pipes.cargo.write_packageurls_to_file")
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

        repo = Mock()
        store_cargo_packages(packages, repo)

        mock_write.assert_called_once()
        args, kwargs = mock_write.call_args
        called_repo, base_purl, written_packages = args

        self.assertEqual(called_repo, repo)

        expected_base_purl = 'aboutcode-packages-cargo-0/cargo/c5store/purls.yml'
        self.assertEqual(str(base_purl), str(expected_base_purl))
        self.assertEqual(written_packages, expected)

    def test_add_purl_result_with_mock_repo(self):
        purls = [{"purl": "pkg:pypi/django@4.2.0"}, {"purl": "pkg:pypi/django@4.3.0"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            mock_repo = mock.MagicMock()
            mock_repo.working_dir = str(repo_dir)
            mock_repo.index.add = mock.MagicMock()

            purls_file = repo_dir / "purls.yaml"

            relative_path = write_packageurls_to_file(mock_repo, purls_file, purls)

            written_file = repo_dir / relative_path
            self.assertTrue(written_file.exists())

            with open(written_file, encoding="utf-8") as f:
                content = saneyaml.load(f)
            self.assertEqual(content, purls)