#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import socket


PRODUCTION_HOSTNAME = 'TBD'

hostname = socket.gethostname()

if hostname.endswith(PRODUCTION_HOSTNAME):
    from minecodeio.settings.production import *
else:
    from minecodeio.settings.dev import *

# DO NOT ADD ANYTHING MORE HERE
