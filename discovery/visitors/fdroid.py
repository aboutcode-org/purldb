#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import codecs
import json
import xmlrpc

from packageurl import PackageURL

from discovery import seed
from discovery import visit_router
from discovery.utils import get_temp_file
from discovery.visitors import HttpJsonVisitor
from discovery.visitors import URI
from discovery.visitors import Visitor
from discovery.visitors import NonPersistentHttpVisitor

"""
Visitors for F-Droid package repositories.

NOTE: the license of F-Droid package data needs to be clarified.
See https://gitlab.com/fdroid/fdroiddata/-/issues/2826 for details

F-Droid packages come with a main JSON index and possible increment/diffs.
- https://f-droid.org/repo/index-v2.json

- this is a legacy XMl index https://f-droid.org/repo/index.xml

- This top level file lists index and diffs https://f-droid.org/repo/entry.json

- This is a diff example: https://f-droid.org/repo/diff/1666980277000.json

- Each apk is available from a URL using this form:

    https://f-droid.org/repo/app.seeneva.reader_3.apk
    https://f-droid.org/repo/{application_id}_{version_code}.apk

The {application_id}_{version_code}.apk "file name" for each tarball and
apk file name is listed in the index.
"""


class FdroidSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://f-droid.org/repo/index-v2.json'


def build_purl(package_id, version_code, filename):
    """
    Return a PackageURL for an F-Droid package.
    """
    return PackageURL(
        type='fdroid',
        name=package_id,
        version=version_code,
        qualifiers=dict(filename=filename)
    )


@visit_router.route('https://f-droid.org/repo/index-v2.json')
class FdroidIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect package metadata URIs from the F-Droid index for each package.
    We treat each apk and corresponding source tarball as a different package.
    """

    def get_uris(self, content):
        """
        Yield a URI for each F-Droid package.
        """
        json_location = content
        with open(json_location) as c:
            content = json.loads(c.read())

        packages = content['packages']

        for package_id, package_data in packages.items():
            purl = PackageURL(type='fdroid', name=package_id).to_string()
            yield URI(
                uri=purl,
                package_url=purl,
                source_uri=self.uri,
                data=json.dumps(package_data, separators=(',', ':'), ensure_ascii=False),
                # note: visited is True since there nothing more to visit
                visited=True
            )
