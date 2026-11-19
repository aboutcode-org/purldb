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
from git import Repo

from minecode.pipes import get_commit_at_distance_ahead
from minecode.pipes import load_data_from_yaml_file
from minecode.pipes import sort_packageurls
from minecode.pipes import write_packageurls_to_file


class GetCommitAtDistanceAheadIntegrationTests(TestCase):
    def setUp(self):
        # Create a temporary directory and init a repo
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.tmpdir.name)
        self.repo = Repo.init(self.repo_path)

        # Configure identity (needed for commits)
        with self.repo.config_writer() as cw:
            cw.set_value("user", "name", "Test User")
            cw.set_value("user", "email", "test@example.com")

        # Create 5 commits
        self.commits = []
        for i in range(5):
            file_path = self.repo_path / f"file{i}.txt"
            file_path.write_text(f"content {i}")
            self.repo.index.add([str(file_path)])
            commit = self.repo.index.commit(f"commit {i}")
            self.commits.append(commit.hexsha)

        # By construction, self.commits[0] = first commit, self.commits[-1] = latest commit

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_get_commit_at_distance_none_current_commit(self):
        # If current_commit is None, it should start from the empty tree hash
        result = get_commit_at_distance_ahead(
            self.repo, None, num_commits_ahead=3, branch_name="master"
        )
        # Should return the 3rd commit in history
        self.assertEqual(result, self.commits[2])

    def test_get_commit_at_distance(self):
        # current_commit = first commit, ask for 3 commits ahead
        result = get_commit_at_distance_ahead(
            self.repo, self.commits[0], num_commits_ahead=3, branch_name="master"
        )
        # Should return the 3rd commit from start (self.commits[3])
        self.assertEqual(result, self.commits[3])

    def test_raises_if_not_enough_commits(self):
        # From latest commit, ask for 10 ahead (only 0 available)
        with self.assertRaises(ValueError) as cm:
            get_commit_at_distance_ahead(
                self.repo, self.commits[-1], num_commits_ahead=10, branch_name="master"
            )
        self.assertIn("Not enough commits ahead; only 0 available.", str(cm.exception))


class SortPackageURLsTests(TestCase):
    def test_sort_packageurls_sorts_cargo_versions_by_semver(self):
        purls = [
            "pkg:cargo/tui-lipan@0.38.4",
            "pkg:cargo/tui-lipan@0.39.0",
            "pkg:cargo/tui-lipan@0.4.0",
            "pkg:cargo/tui-lipan@0.4.1",
            "pkg:cargo/tui-lipan@0.5.0",
        ]
        expected = [
            "pkg:cargo/tui-lipan@0.4.0",
            "pkg:cargo/tui-lipan@0.4.1",
            "pkg:cargo/tui-lipan@0.5.0",
            "pkg:cargo/tui-lipan@0.38.4",
            "pkg:cargo/tui-lipan@0.39.0",
        ]
        self.assertEqual(expected, sort_packageurls(purls))

    def test_sort_packageurls_uses_the_version_scheme_of_the_purl_type(self):
        purls = [
            "pkg:pypi/django@1.10.0",
            "pkg:pypi/django@1.9.0",
            "pkg:pypi/django@1.10.0rc1",
            "pkg:maven/org.apache/commons@2.10",
            "pkg:maven/org.apache/commons@2.9",
        ]
        expected = [
            "pkg:maven/org.apache/commons@2.9",
            "pkg:maven/org.apache/commons@2.10",
            "pkg:pypi/django@1.9.0",
            "pkg:pypi/django@1.10.0rc1",
            "pkg:pypi/django@1.10.0",
        ]
        self.assertEqual(expected, sort_packageurls(purls))

    def test_sort_packageurls_groups_by_package(self):
        purls = [
            "pkg:npm/zlib@1.10.0",
            "pkg:npm/abc@2.0.0",
            "pkg:npm/zlib@1.9.0",
            "pkg:npm/abc@10.0.0",
        ]
        expected = [
            "pkg:npm/abc@2.0.0",
            "pkg:npm/abc@10.0.0",
            "pkg:npm/zlib@1.9.0",
            "pkg:npm/zlib@1.10.0",
        ]
        self.assertEqual(expected, sort_packageurls(purls))

    def test_sort_packageurls_puts_unparsable_versions_after_valid_ones(self):
        purls = [
            "pkg:pypi/foo@not-a-version",
            "pkg:pypi/foo@1.10",
            "pkg:pypi/foo@1.9",
            "pkg:pypi/foo",
        ]
        expected = [
            "pkg:pypi/foo@1.9",
            "pkg:pypi/foo@1.10",
            "pkg:pypi/foo@not-a-version",
            "pkg:pypi/foo",
        ]
        self.assertEqual(expected, sort_packageurls(purls))

    def test_sort_packageurls_sorts_types_without_version_scheme_by_string(self):
        purls = [
            "pkg:alpine/curl@8.10.0-r0",
            "pkg:alpine/curl@8.9.1-r0",
        ]
        expected = [
            "pkg:alpine/curl@8.10.0-r0",
            "pkg:alpine/curl@8.9.1-r0",
        ]
        self.assertEqual(expected, sort_packageurls(purls))

    def test_sort_packageurls_is_stable_for_qualifiers_of_the_same_version(self):
        purls = [
            "pkg:maven/org.apache/commons@2.10?classifier=sources",
            "pkg:maven/org.apache/commons@2.10",
            "pkg:maven/org.apache/commons@2.9?classifier=sources",
        ]
        expected = [
            "pkg:maven/org.apache/commons@2.9?classifier=sources",
            "pkg:maven/org.apache/commons@2.10",
            "pkg:maven/org.apache/commons@2.10?classifier=sources",
        ]
        self.assertEqual(expected, sort_packageurls(purls))


class WritePackageURLsToFileTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo = Repo.init(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_write_packageurls_to_file_sorts_by_version(self):
        path = write_packageurls_to_file(
            repo=self.repo,
            relative_datafile_path="cargo/tui-lipan/purls.yml",
            packageurls=["pkg:cargo/tui-lipan@0.39.0", "pkg:cargo/tui-lipan@0.4.0"],
        )
        result = load_data_from_yaml_file(Path(self.tmpdir.name) / path)
        expected = ["pkg:cargo/tui-lipan@0.4.0", "pkg:cargo/tui-lipan@0.39.0"]
        self.assertEqual(expected, result)

    def test_write_packageurls_to_file_append_merges_and_sorts_by_version(self):
        relative_path = "cargo/tui-lipan/purls.yml"
        write_packageurls_to_file(
            repo=self.repo,
            relative_datafile_path=relative_path,
            packageurls=["pkg:cargo/tui-lipan@0.4.0", "pkg:cargo/tui-lipan@0.38.4"],
        )
        write_packageurls_to_file(
            repo=self.repo,
            relative_datafile_path=relative_path,
            packageurls=["pkg:cargo/tui-lipan@0.39.0", "pkg:cargo/tui-lipan@0.4.0"],
            append=True,
        )
        result = load_data_from_yaml_file(Path(self.tmpdir.name) / relative_path)
        expected = [
            "pkg:cargo/tui-lipan@0.4.0",
            "pkg:cargo/tui-lipan@0.38.4",
            "pkg:cargo/tui-lipan@0.39.0",
        ]
        self.assertEqual(expected, result)
