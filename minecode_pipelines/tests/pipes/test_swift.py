#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
from unittest import TestCase
import saneyaml
from minecode_pipelines.pipes.swift import (
    get_tags_and_commits_from_git_output,
    generate_package_urls,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "swift"


def logger(msg):
    print(msg)


class SwiftPipelineTests(TestCase):
    def _run_package_test(self, package_repo_url, commits_tags_file, expected_file):
        with open(commits_tags_file, encoding="utf-8") as f:
            git_ls_remote = f.read()

        with open(expected_file, encoding="utf-8") as f:
            expected_purls = saneyaml.load(f)

        tags_and_commits = get_tags_and_commits_from_git_output(git_ls_remote)

        base_purl, generated_purls = generate_package_urls(
            package_repo_url=package_repo_url,
            tags_and_commits=tags_and_commits,
            logger=logger,
        )

        result_purls = sorted(str(p) for p in generated_purls)
        assert result_purls == sorted(expected_purls)

    def test_swift_safe_collection_access(self):
        self._run_package_test(
            package_repo_url="https://github.com/RougeWare/Swift-Safe-Collection-Access",
            commits_tags_file=DATA_DIR / "commits_tags1.txt",
            expected_file=DATA_DIR / "expected1.yaml",
        )

    def test_human_string(self):
        self._run_package_test(
            package_repo_url="https://github.com/zonble/HumanString.git",
            commits_tags_file=DATA_DIR / "commits_tags2.txt",
            expected_file=DATA_DIR / "expected2.yaml",
        )

    def test_swift_financial(self):
        self._run_package_test(
            package_repo_url="https://github.com/zrluety/SwiftFinancial.git",
            commits_tags_file=DATA_DIR / "commits_tags3.txt",
            expected_file=DATA_DIR / "expected3.yaml",
        )

    def test_swift_xcf_sodium(self):
        self._run_package_test(
            package_repo_url="https://github.com/0xacdc/XCFSodium",
            commits_tags_file=DATA_DIR / "commits_tags4.txt",
            expected_file=DATA_DIR / "expected4.yaml",
        )
