#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from minecode.utils_test import MiningTestCase
from minecode.filter import sf_net


class FilterTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_filter(self):
        inputf = self.get_test_loc('filter_sf/tst_sfnet.csv')
        exf = self.get_test_loc('filter_sf/tst_sfnet2.csv')
        expected = open(exf, 'rb').read()
        tdir = self.get_temp_dir()
        output = os.path.join(tdir, 'out.csv')
        sf_net(inputf, output)
        test = open(output, 'rb').read()
        self.assertEqual(expected, test)
