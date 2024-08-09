#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os

from minecode.utils_test import MiningTestCase
from minecode.miners import repodata_rpms


class RepodataRPMVisitorsTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_collect_rsync_urls(self):
        directory_listing_loc = self.get_test_loc(
            'repodata_rpms/centos_dir_listing')
        base_url = 'http://mirrors.kernel.org/centos/'
        uris = repodata_rpms.collect_rsync_urls(
            directory_listing_loc, base_url, file_names=('repomd.xml',))
        uris = list(uris)
        self.assertEqual(1, len(uris))
