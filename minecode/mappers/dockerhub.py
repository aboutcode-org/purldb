#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode import models as scan_models

from minecode import map_router
from minecode.mappers import Mapper


@map_router.route('https://registry.hub.docker.com/v2/repositories/library/[\w\-\.]+/')
class DockerHubLiraryJsonMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_jsonfile(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_jsonfile(metadata, uri=None, purl=None):
    """
    Yield Package built from Docker Hub json content.
    metadata: json metadata content
    uri: String value of uri of the ResourceURI object.
    purl: String value of the package url of the ResourceURI object
    """
    content = json.loads(metadata)
    dockhub_library_htmlpage_template = 'https://hub.docker.com/_/{project}'
    name = content.get('name')
    if name:
        short_desc = content.get('description')
        long_desc = content.get('full_description')
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = '\n'.join(descriptions)
        common_data = dict(
            type='docker',
            name=name,
            description=description,
            homepage_url=dockhub_library_htmlpage_template.format(project=name),
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
