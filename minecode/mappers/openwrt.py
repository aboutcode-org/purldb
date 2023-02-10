#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging

from packagedcode import models as scan_models

from minecode import debutils
from minecode import map_router
from minecode.mappers import Mapper
from minecode.mappers.debian import get_dependencies


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


"""
OpenWRT IPK package data files are using the Deb822 format.
"""


@map_router.route('https://downloads.openwrt.org/.*\.ipk')
class OpenwrtIpkMetadataMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackage built from resource_uri record for a single package
        version. Yield as many Package as there are download URLs.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages(metadata, resource_uri.package_url)


def build_packages(metadata, purl=None):
    """
    Yield ScannedPackage built from the passing metadata.
    metadata: metadata mapping
    purl: String value of the package url of the ResourceURI object
    """
    common_data = dict(
        type='openwrt',
        name=metadata.get('Package'),
        version=metadata.get('Version'),
        description=metadata.get('Description'),
        size=metadata.get('Installed-Size'),
    )

    dependencies = get_dependencies(metadata, ['Depends'])
    if dependencies:
        common_data['dependencies'] = dependencies

    maintainers = metadata.get('Maintainer')
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            parties = common_data.get('parties')
            if not parties:
                common_data['parties'] = []
            party = scan_models.Party(name=name, role='maintainer', email=email)
            common_data['parties'].append(party)

    lic = metadata.get('License')
    if lic:
        common_data['declared_license'] = lic

    common_data['keywords'] = []
    section = metadata.get('Section')
    if section:
        common_data['keywords'].append(section)
    architecture = metadata.get('Architecture')
    if architecture:
        common_data['keywords'].append(architecture)
    package = scan_models.Package(**common_data)
    package.set_purl(purl)
    yield package
