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
    get_tags_and_commits_from_git_output,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "swift"


class SwiftPipelineTests(TestCase):
    def _run_package_test(
        self, package_repo_url, commits_tags_file, expected_file, expected_path_parts
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

    def test_human_string(self):
        self._run_package_test(
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

    def test_swift_financial(self):
        self._run_package_test(
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

    def test_swift_xcf_sodium(self):
        self._run_package_test(
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
