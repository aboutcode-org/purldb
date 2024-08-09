#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

import packagedcode.models as scan_models

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import form_vcs_url
from minecode.utils import parse_date


@map_router.route('https://gitlab.com/.*')
class GitLabMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_json(metadata, resource_uri.package_url)


def build_packages_from_json(metadata, purl=None):
    """
    Yield Package built from gitlab json content
    metadata: Json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    content = json.loads(metadata)

    name = content.get('name')
    if name:
        common_data = dict(
            type='gitlab',
            name=name,
            homepage_url=content.get('web_url'),
            description=content.get('description'),
        )
        repo_url = content.get('http_url_to_repo')
        if repo_url:
            repo_url = form_vcs_url('git', repo_url)
            common_data['vcs_url'] = repo_url
        common_data['code_view_url'] = repo_url
        common_data['release_date'] = parse_date(content.get('created_at'))
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
