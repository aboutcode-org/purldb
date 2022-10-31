#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os

from discovery import command
from discovery import ON_WINDOWS
from discovery.utils_test import MiningTestCase


class CommandTest(MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_listing_command(self):
        td = self.get_test_loc('command')
        osc = 'ls' if not ON_WINDOWS else 'dir'
        c = '%(osc)s "%(td)s"' % locals()
        cmd = command.Command(c)
        out, err = cmd.execute()
        err = [e for e in err]
        self.assertEqual([], err)

        out = [o for o in out]
        self.assertTrue(any('foo' in i for i in out))
        self.assertTrue(any('bar' in i for i in out))
        self.assertTrue(all(i.endswith('\n') for i in out))
