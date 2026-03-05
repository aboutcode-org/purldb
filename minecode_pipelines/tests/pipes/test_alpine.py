#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from unittest.mock import patch

from commoncode.testcase import check_against_expected_json_file
from commoncode.testcase import FileBasedTesting

from minecode_pipelines.pipes import alpine


class AlpineMapperTest(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_parse_apkindex_and_build_package(self):
        index_location = self.get_test_loc("alpine/APKINDEX")
        packages = []
        with open(index_location, encoding="utf-8") as f:
            for pkg in alpine.parse_apkindex(f.read()):
                pd = alpine.build_package(pkg, distro="v3.22", repo="community")
                packages.append(pd.to_dict())
        expected_loc = self.get_test_loc("alpine/expected_packages.json")
        check_against_expected_json_file(packages, expected_loc, regen=False)

    def test_mine_and_publish_skips_processed_indexes(self):
        """Test that already-processed index URLs are skipped."""
        all_urls = alpine.ALPINE_LINUX_APKINDEX_URLS
        processed_indexes = set(all_urls[1:])
        calls = []

        def mock_mine_and_publish(**kwargs):
            calls.append(kwargs.get("packageurls"))

        with patch(
            "minecode_pipelines.pipes.alpine._mine_and_publish_packageurls",
            side_effect=mock_mine_and_publish,
        ):
            alpine.mine_and_publish_alpine_packageurls(
                data_cluster=None,
                checked_out_repos={},
                working_path=None,
                commit_msg_func=lambda *a, **kw: "test",
                logger=lambda msg: None,
                processed_indexes=processed_indexes,
            )
        self.assertEqual(len(calls), 1)

    def test_mine_and_publish_updates_processed_indexes(self):
        """Test that processed_indexes is updated after each index."""
        processed_indexes = set()

        with patch(
            "minecode_pipelines.pipes.alpine._mine_and_publish_packageurls",
        ):
            original_urls = alpine.ALPINE_LINUX_APKINDEX_URLS
            alpine.ALPINE_LINUX_APKINDEX_URLS = original_urls[:2]
            try:
                alpine.mine_and_publish_alpine_packageurls(
                    data_cluster=None,
                    checked_out_repos={},
                    working_path=None,
                    commit_msg_func=lambda *a, **kw: "test",
                    logger=lambda msg: None,
                    processed_indexes=processed_indexes,
                )
            finally:
                alpine.ALPINE_LINUX_APKINDEX_URLS = original_urls

        self.assertEqual(len(processed_indexes), 2)
        self.assertIn(original_urls[0], processed_indexes)
        self.assertIn(original_urls[1], processed_indexes)
