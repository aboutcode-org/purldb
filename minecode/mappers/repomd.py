#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode.models import PackageData

from minecode import map_router


@map_router.route(".+/repomd.xml")
def map_repomd_data(uris, resource_uri):
    """Return a list of RpmPackage objects collected from visitors."""
    if not resource_uri.data:
        return
    packages = []
    for pkg_data in json.loads(resource_uri.data):
        # 'name' is required for every package
        # FIXME: how could we obtain a package without a name???
        # FIXME: This cannot work unless we use **pkg_data
        if pkg_data.get("name"):
            packages.append(PackageData(pkg_data))
    return packages
