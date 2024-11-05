#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from unittest.mock import MagicMock
from unittest.mock import patch

from github.Download import Download
from github.Repository import Repository

from minecode import miners
from minecode.miners import github
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import mocked_requests_get


class GithubVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    @patch("github.MainClass.Github.get_repo")
    def test_GithubRepoVisitor(self, mock_get_repo):
        repository = MagicMock(spec=Repository)
        repository.name = "grit"
        repository.size = 7954
        repository.id = 1
        repository.description = "**Grit is no longer maintained. Check out libgit2/rugged.** Grit gives you object oriented read/write access to Git repositories via Ruby."
        repository.language = "Ruby"
        repository.homepage = "http://grit.rubyforge.org/"
        repository._issues_url = None
        repository._git_url = None
        repository.html_url = "https://github.com/mojombo/grit"
        repository.svn_url = None
        repository.etag = None
        repository.clone_url = "https://github.com/mojombo/grit.git"
        repository.watchers = None
        repository.full_name = "mojombo/grit"
        repository.ssh_url = "git@github.com:mojombo/grit.git"
        repository.owner = None
        repository.blobs_url = None
        repository.master_branch = None
        repository.updated_at = None
        repository.pushed_at = None

        download = MagicMock(spec=Download)
        download.name = "grit-1.0.1.gem"
        download.redirect = None
        download.description = None
        download.url = "https://api.github.com/repos/mojombo/grit/downloads/5"
        download.size = 1861632
        download.s3_url = None
        download.created_at = None
        download.download_count = 187
        download.redirect = None
        download.signature = None
        download.html_url = "https://github.com/downloads/mojombo/grit/grit-1.0.1.gem"
        download.bucket = None
        download.acl = None
        download.accesskeyid = None
        download.expirationdate = None
        repository.get_downloads.return_value = iter([download])

        tag = MagicMock()
        tag.name = "tags"
        tag.zipball_url = "https://api.github.com/repos/mojombo/grit/zipball/v2.5.0"
        tag.tarball_url = "https://api.github.com/repos/mojombo/grit/tarball/v2.5.0"
        tag.name = "v2.5.0"
        tag.commit = None
        repository.get_tags.return_value = iter([tag])

        label = MagicMock()
        label.name = "label 1"
        repository.get_labels.return_value = iter([label])

        mock_get_repo.return_value = repository

        uri = "https://api.github.com/repos/mojombo/grit"
        _, data, _ = github.GithubSingleRepoVisitor(uri)
        expected_loc = self.get_test_loc("github/mojombo_grit_expected.json")
        self.check_expected_results(data, expected_loc, regen=FIXTURES_REGEN)

    @patch("github.MainClass.Github.get_repo")
    def test_GithubRepoVisitor_without_tag_without_download(self, mock_get_repo):
        repository = MagicMock(spec=Repository)
        repository.name = "calendar_builder"
        repository.size = 188
        repository.id = 367
        repository.description = None
        repository.language = "Ruby"
        repository.homepage = None
        repository._issues_url = None
        repository._git_url = None
        repository.html_url = "https://github.com/collectiveidea/calendar_builder"
        repository.svn_url = None
        repository.etag = '"e10b78ff74a199fcf802be4afc333275"'
        repository.clone_url = "git@github.com:collectiveidea/calendar_builder.git"
        repository.watchers = None
        repository.full_name = "collectiveidea/calendar_builder"
        repository.ssh_url = "git@github.com:collectiveidea/calendar_builder.git"
        repository.owner = None
        repository.blobs_url = "https://api.github.com/repos/collectiveidea/calendar_builder/git/blobs{/sha}"
        repository.master_branch = None
        repository.updated_at = None
        repository.pushed_at = None

        repository.get_downloads.return_value = None
        repository.get_tags.return_value = None
        repository.get_labels.return_value = None

        master_branch = MagicMock()
        master_branch.name = "master"
        refactoring_branch = MagicMock()
        refactoring_branch.name = "refactoring"
        repository.get_branches.return_value = iter([master_branch, refactoring_branch])
        mock_get_repo.return_value = repository
        uri = "https://api.github.com/repos/collectiveidea/calendar_builder"
        _, data, _ = github.GithubSingleRepoVisitor(uri)
        expected_loc = self.get_test_loc("github/calendar_builder-expected.json")
        self.check_expected_results(data, expected_loc, regen=FIXTURES_REGEN)

    def test_GithubReposVisitor(self):
        uri = "https://api.github.com/repositories?since=0"
        test_loc = self.get_test_loc("github/repo_since0.json")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = github.GithubReposVisitor(uri)
        expected_loc = self.get_test_loc("github/repo_since0_expected.json")
        self.check_expected_results(data, expected_loc)


class GithubMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def test_github_repo_mapper1(self):
        with open(self.get_test_loc("github/calendar_builder.json")) as json_metadata:
            metadata = json_metadata.read()
        packages = miners.github.build_github_packages(
            metadata, "https://api.github.com/repos/collectiveidea/calendar_builder"
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc("github/mapper_calendar_builder_expected.json")
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)

    def test_github_repo_mapper2(self):
        with open(
            self.get_test_loc("github/mojombo_grit_from_visitor_4mapper_input.json")
        ) as json_metadata:
            metadata = json_metadata.read()
        packages = miners.github.build_github_packages(
            metadata, "https://api.github.com/repos/mojombo/grit"
        )
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc(
            "github/mojombo_grit_result_mapper_expected.json"
        )
        self.check_expected_results(packages, expected_loc, regen=FIXTURES_REGEN)
