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
from unittest import TestCase
from unittest.mock import Mock, patch
import saneyaml
from minecode_pipelines.pipes.swift import (
    store_swift_packages,
    get_tags_and_commits_from_git_output,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "swift"


class SwiftPipelineTests(TestCase):
    def _run_package_test(
        self, mock_write, package_repo_url, commits_tags_file, expected_file, expected_path_parts
    ):
        # Load test input and expected output
        with open(commits_tags_file, encoding="utf-8") as f:
            git_ls_remote = f.read()
        with open(expected_file, encoding="utf-8") as f:
            expected = saneyaml.load(f)

        # Create a temporary working directory for the repo
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Mock()
            repo.working_dir = tmpdir

            # Execute function under test
            tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)
            store_swift_packages(package_repo_url, tags_and_commits, repo)

            # Verify function call
            mock_write.assert_called_once()
            _, kwargs = mock_write.call_args
            base_purl, written_packages = kwargs["path"], kwargs["data"]

            # Expected file path
            expected_base_purl = Path(tmpdir).joinpath(*expected_path_parts)

            self.assertEqual(str(base_purl), str(expected_base_purl))
            self.assertEqual(written_packages, expected)

    @patch("minecode_pipelines.pipes.swift.write_data_to_yaml_file")
    def test_swift_safe_collection_access(self, mock_write):
        self._run_package_test(
            mock_write,
            package_repo_url="https://github.com/RougeWare/Swift-Safe-Collection-Access",
            commits_tags_file=DATA_DIR / "commits_tags1.txt",
            expected_file=DATA_DIR / "expected1.yaml",
            expected_path_parts=[
                "aboutcode-packages-swift-0",
                "swift",
                "github.com",
                "RougeWare",
                "Swift-Safe-Collection-Access",
                "purls.yml",
            ],
        )

    @patch("minecode_pipelines.pipes.swift.write_data_to_yaml_file")
    def test_human_string(self, mock_write):
        self._run_package_test(
            mock_write,
            package_repo_url="https://github.com/zonble/HumanString.git",
            commits_tags_file=DATA_DIR / "commits_tags2.txt",
            expected_file=DATA_DIR / "expected2.yaml",
            expected_path_parts=[
                "aboutcode-packages-swift-0",
                "swift",
                "github.com",
                "zonble",
                "HumanString",
                "purls.yml",
            ],
        )

    @patch("minecode_pipelines.pipes.swift.write_data_to_yaml_file")
    def test_swift_financial(self, mock_write):
        self._run_package_test(
            mock_write,
            package_repo_url="https://github.com/zrluety/SwiftFinancial.git",
            commits_tags_file=DATA_DIR / "commits_tags3.txt",
            expected_file=DATA_DIR / "expected3.yaml",
            expected_path_parts=[
                "aboutcode-packages-swift-0",
                "swift",
                "github.com",
                "zrluety",
                "SwiftFinancial",
                "purls.yml",
            ],
        )

    @patch("minecode_pipelines.pipes.swift.write_data_to_yaml_file")
    def test_swift_xcf_sodium(self, mock_write):
        self._run_package_test(
            mock_write,
            package_repo_url="https://github.com/0xacdc/XCFSodium",
            commits_tags_file=DATA_DIR / "commits_tags4.txt",
            expected_file=DATA_DIR / "expected4.yaml",
            expected_path_parts=[
                "aboutcode-packages-swift-0",
                "swift",
                "github.com",
                "0xacdc",
                "XCFSodium",
                "purls.yml",
            ],
        )
