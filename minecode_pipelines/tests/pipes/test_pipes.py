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

from minecode_pipelines.pipes import get_commit_at_distance_ahead


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
