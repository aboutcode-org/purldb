#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import sys

from discovery import route


default_app_config = 'discovery.apps.DiscoveryConfig'


sys_platform = str(sys.platform).lower()
ON_WINDOWS = 'win32' in sys_platform
ON_MAC = 'darwin' in sys_platform
ON_LINUX = 'linux' in sys_platform

# global instances of our routers
visit_router = route.Router()
map_router = route.Router()
