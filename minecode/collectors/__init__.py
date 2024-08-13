#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import pkgutil

"""
Minimal way to recursively import all submodules dynamically. If this module is
imported, all submodules will be imported: this triggers the actual registration
of miners. This should stay as the last import in this init module.
"""
for _, name, _ in pkgutil.walk_packages(__path__, prefix=__name__ + "."):
    __import__(name)
