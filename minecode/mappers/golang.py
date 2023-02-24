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
from packageurl import PackageURL

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import form_vcs_url


@map_router.route('pkg:golang/.*')
class GolangApiDocMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        package = json.loads(resource_uri.data)
        yield build_golang_package(package, resource_uri.package_url)


def build_golang_package(package_data, purl):
    """
    Return a single Golang package
    """
    package_url = PackageURL.from_string(purl)
    vcs_url = package_url.qualifiers.get('vcs_repository')
    homepage_url = '/'.join(['https:/', package_url.namespace, package_url.name])
    vcs_tool = 'git' if 'github.com' in package_url.namespace else None
    if vcs_tool:
        vcs_url = form_vcs_url(vcs_tool, vcs_url)
    # TODO: collect stats and counter from package_data too
    package = scan_models.Package(
        name=package_url.name,
        namespace=package_url.namespace,
        type=package_url.type,
        primary_language='Go',
        description=package_data.get('synopsis'),
        homepage_url=homepage_url,
        vcs_url=vcs_url,
    )
    return package
