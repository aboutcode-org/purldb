#!/usr/bin/python
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os

from minecode.miners import repodata_rpms
from minecode.utils_test import MiningTestCase


class RepodataRPMVisitorsTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_collect_rsync_urls(self):
        directory_listing_loc = self.get_test_loc("repodata_rpms/centos_dir_listing")
        base_url = "http://mirrors.kernel.org/centos/"
        uris = repodata_rpms.collect_rsync_urls(
            directory_listing_loc, base_url, file_names=("repomd.xml",)
        )
        uris = list(uris)
        self.assertEqual(1, len(uris))
