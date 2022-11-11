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

from discovery import map_router
from discovery.mappers import Mapper


@map_router.route('https?://sourceforge.net/api/project/name/[a-z0-9.-]+/json',
                  'https?://sourceforge.net/rest/p/[a-z0-9.-]+')
class SourceforgeProjectJsonAPIMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_from_metafile(metadata, resource_uri.package_url)


def build_packages_from_metafile(metadata, purl=None):
    """
    Yield Package built from package a `metadata` content
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    short_desc = metadata.get('summary')
    long_desc = metadata.get('short_description')
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = '\n'.join(descriptions)
    name = metadata.get('shortname')
    # short name is more reasonable here for name, since it's an abbreviation
    # for the project and unique
    if not name:
        name = metadata.get('name')
    if name:
        common_data = dict(
            type='sourceforge',
            name=metadata.get('shortname', metadata.get('name')),
            description=description,
            homepage_url=metadata.get('external_homepage', metadata.get('url')),
        )

        devs = metadata.get('developers') or []
        for dev in devs:
            parties = common_data.get('parties')
            if not parties:
                common_data['parties'] = []
            if dev.get('name'):
                common_data['parties'].append(
                    scan_models.Party(name=dev.get('name'), role='contributor', url=dev.get('url')))

        categories = metadata.get('categories', {})
        languages = categories.get('language', [])
        langs = []
        for lang in languages:
            lshort = lang.get('shortname')
            if lshort:
                langs.append(lshort)
        langs = ', '.join(langs)
        common_data['primary_language'] = langs or None

        declared_licenses = []
        licenses = categories.get('license') or []
        for l in licenses:
            license_name = l.get('fullname')
            # full name is first priority than shortname since shortname is like gpl, it doesn't show detailed gpl version etc.
            if license_name:
                declared_licenses.append(l.get('shortname'))
            if license_name:
                declared_licenses.append(license_name)
        if declared_licenses:
            common_data['declared_license'] = '\n'.join(declared_licenses)

        keywords = []
        topics = categories.get('topic', [])
        for topic in topics:
            keywords.append(topic.get('shortname'))
        common_data['keywords'] = keywords or None
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
