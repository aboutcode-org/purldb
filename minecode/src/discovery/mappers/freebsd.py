#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from io import StringIO
import os
import saneyaml

from packagedcode.freebsd import CompactManifestHandler

from discovery import map_router
from discovery.mappers import Mapper
from discovery.utils import get_temp_dir


@map_router.route('https://pkg.freebsd.org/.*packagesite.txz')
class FreeBSDIndexMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        return build_packages(resource_uri.data, resource_uri.package_url)


def build_packages(metadata, purl=None):
    """
    Yield the package by parsing the passing json content.
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    buf = StringIO(metadata)
    # The passing metadata is not a well-formatted yaml or json, but each line is a yaml, so read by line and parse with FreeBSDPackage parser.
    for each_line in buf:
        if each_line and each_line.strip() in ('', '{', '}'):
            continue
        content = saneyaml.load(each_line)
        if content and content.get('name'):
            temp_dir = get_temp_dir('freebsd_index')
            location = os.path.join(temp_dir, '+COMPACT_MANIFEST')
            with open(location, 'w') as manifest:
                manifest.write(each_line)
            with open(location, encoding='utf-8') as loc:
                yaml_data = saneyaml.load(loc)
            package = CompactManifestHandler._parse(yaml_data=yaml_data)
            package.set_purl(purl)
            yield package
