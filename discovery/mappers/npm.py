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


from packagedcode.npm import NpmPackageJsonHandler

from discovery import map_router
from discovery.mappers import Mapper


TRACE = False

logger = logging.getLogger(__name__)

if TRACE:
    import sys
    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


# FIXME: This route may not work when we have scoped Packages or URLs to a specific version
# or yarn URLs
@map_router.route('https://registry.npmjs.org/[^\/]+')
class NpmPackageMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield NpmPackage built from a resource_uri record that contains many
        npm versions for a given npm name.
        """
        if not resource_uri.data:
            return
        visited_data = json.loads(resource_uri.data)
        return build_packages(visited_data)


# FIXME: Consider using PURL here
def build_packages(data):
    """
        Yield NpmPackage built from data corresponding to a single package name
        and many npm versions.
    """
    versions = data.get('versions', {})

    logger.debug('build_packages: versions: ' + repr(type(versions)))
    for version, data in versions.items():
        logger.debug('build_packages: version: ' + repr(version))
        logger.debug('build_packages: data: ' + repr(data))
        package = NpmPackageJsonHandler._parse(json_data=data)
        if package:
            yield package
