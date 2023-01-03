#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import sys

from packagedb.models import Package


def dump_purls(package_type, output):
    """
    Dump packagedb purls for ``package_type`` as JSON lines in the ``output`` files
    """
    compact_separators = (u',', u':',)
    out = None
    for i, package in enumerate(Package.objects.filter(type=package_type).all()):
        if not output:
            out = open(f"{output}-{i}.json", "w")
        purl = dict(purl=package.package_url, download_url=package.download_url)
        if not i % 500:
            print(f"#{i} purl: {package.package_url}")
        out.write(json.dumps(purl, separators=compact_separators))
        out.write('\n')
        if not i % 1000000:
            out.close()
            out = None


if __name__ == "__main__":
    args = sys.argv[1:]
    package_type = args[0]
    output = args[1]
    dump_purls(package_type=package_type, output=output)

