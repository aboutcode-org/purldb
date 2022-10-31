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
from packagedcode.models import DependentPackage
from packagedcode.models import PackageData

from discovery import map_router
from discovery import saneyaml
from discovery.mappers import Mapper
from discovery.utils import parse_date

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@map_router.route('https*://rubygems\.org/api/v1/versions/[\w\-\.]+.json')
class RubyGemsApiVersionsJsonMapper(Mapper):
    """
    Mapper to build Rubygems Packages from JSON API data.
    """

    def get_packages(self, uri, resource_uri):
        metadata = json.loads(resource_uri.data)
        _, sep, namejson = uri.partition('versions/')
        if not sep:
            return
        name, sep, _ = namejson.rpartition('.json')
        if not sep:
            return
        return build_rubygem_packages_from_api_data(metadata, name)


def build_rubygem_packages_from_api_data(metadata, name, purl=None):
    """
    Yield Package built from resource_uri record for a single
    package version.
    metadata: json metadata content
    name: package name
    purl: String value of the package url of the ResourceURI object
    """
    for version_details in metadata:
        short_desc = version_details.get('summary')
        long_desc = version_details.get('description')
        if long_desc == short_desc:
            long_desc = None
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = '\n'.join(descriptions)
        package = dict(
            type='gem',
            name=name,
            description=description,
            version=version_details.get('number'),
        )
        # FIXME: we are missing deps and more things such as download URL and more

        if version_details.get('sha'):
            package['sha256'] = version_details.get('sha')

        package['release_date'] = parse_date(version_details.get('created_at') or '') or None

        author = version_details.get('authors')
        if author:
            parties = package.get('parties')
            if not parties:
                package['parties'] = []
            party = scan_models.Party(name=author, role='author')
            package['parties'].append(party)

        declared_licenses = []
        licenses = version_details.get('licenses')
        if licenses:
            for lic in licenses:
                declared_licenses.append(lic)
        if declared_licenses:
            package['declared_license'] = '\n'.join(declared_licenses)
        package = PackageData(**package)
        package.set_purl(purl)
        yield package


@map_router.route('https?://rubygems.org/downloads/[\w\-\.]+.gem')
class RubyGemsPackageArchiveMetadataMapper(Mapper):
    """
    Mapper to build on e Package from the metadata file found inside a gem.
    """

    def get_packages(self, uri, resource_uri):
        metadata = resource_uri.data
        return build_rubygem_packages_from_metadata(metadata, download_url=uri)


def build_rubygem_packages_from_metadata(metadata, download_url=None, purl=None):
    """
    Yield Package built from a Gem `metadata` YAML content
    metadata: json metadata content
    download_url: url to download the package
    purl: String value of the package url of the ResourceURI object
    """
    content = saneyaml.load(metadata)
    if not content:
        return

    name = content.get('name')
    short_desc = content.get('summary')
    long_desc = content.get('description')
    if long_desc == short_desc:
        long_desc = None
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = '\n'.join(descriptions)
    package = dict(
        type='gem',
        name=name,
        description=description,
        homepage_url=content.get('homepage'),
    )
    if download_url:
        package['download_url'] = download_url

    declared_licenses = []
    licenses = content.get('licenses')
    if licenses:
        for lic in licenses:
            declared_licenses.append(lic)
    if declared_licenses:
        package['declared_license'] = '\n'.join(declared_licenses)

    authors = content.get('authors')
    for author in authors:
        parties = package.get('parties')
        if not parties:
            package['parties'] = []
        party = scan_models.Party(name=author, role='author')
        package['parties'].append(party)

    # Release date in the form of `2010-02-01 00:00:00 -05:00`
    release_date = content.get('date', '').split()
    package['release_date'] = parse_date(release_date[0])

    package['dependencies'] = get_dependencies_from_meta(content) or []

    # This is a two level nenest item
    version1 = content.get('version') or {}
    version = version1.get('version') or None
    package['version'] = version
    package = PackageData(**package)
    package.set_purl(purl)
    yield package


def get_dependencies_from_meta(content):
    """
    Return a mapping of dependencies keyed by group based on the gem YAML
    metadata data structure.
    """
    dependencies = content.get('dependencies') or []
    if not dependencies:
        return []

    group = []
    for dependency in dependencies:
        name = dependency.get('name') or None
        if not name:
            continue

        requirement = dependency.get('requirement') or {}
        # FIXME when upating to the ScanCode package model
        scope = dependency.get('type')
        scope = scope and scope.lstrip(':')

        # note that as weird artifact of our saneyaml YAML parsing, we are
        # getting both identical requirements and version_requirements mapping.
        # We ignore version_requirements
        # requirement is {'requirements': [
        #                     [u'>=', {'version': '0'}]
        #                   ]
        #                }
        requirements = requirement.get('requirements') or []
        version_constraint = []

        # each requirement is [u'>=', {'version': '0'}]
        for constraint, req_version in requirements:
            req_version = req_version.get('version') or None
            # >= 0 allows for any version: we ignore these type of contrainsts
            # as this is the same as no constraints. We also ignore lack of
            # constraints and versions
            if ((constraint == '>=' and req_version == '0')
                    or not (constraint and req_version)):
                continue
            version_constraint.append(' '.join([constraint, req_version]))
        version_constraint = ', '.join(version_constraint) or None

        group.append(DependentPackage(
            purl=name, extracted_requirement=version_constraint, scope=scope))

    return group


def get_dependencies_from_api(content):
    """
    Return a mapping of dependencies keyed by group based on the RubyGems API
    data structure.
    """
    dependencies = content.get('dependencies') or []
    if not dependencies:
        return {}

    group = []
    for dependency in dependencies:
        name = dependency.get('name') or None
        if not name:
            continue

        requirement = dependency.get('requirement') or {}
        scope = dependency.get('type')
        scope = scope and scope.lstrip(':')

        # note that as weird artifact of our saneyaml YAML parsing, we are
        # getting both identical requirements and version_requirements mapping.
        # We ignore version_requirements
        # requirement is {'requirements': [
        #                     [u'>=', {'version': '0'}]
        #                   ]
        #                }
        requirements = requirement.get('requirements') or []
        version_constraint = []
        # each requirement is [u'>=', {'version': '0'}]
        for constraint, req_version in requirements:
            req_version = req_version.get('version') or None
            # >= 0 allows for any version: we ignore these type of contrainsts
            # as this is the same as no constraints. We also ignore lack of
            # constraints and versions
            if ((constraint == '>=' and req_version == '0')
                    or not (constraint and req_version)):
                continue
            version_constraint.append(' '.join([constraint, req_version]))
        version_constraint = ', '.join(version_constraint) or None

        group.append(DependentPackage(
            purl=name, extracted_requirement=version_constraint, scope=scope))

    return group


# Structure: {gem_spec: license.key}
LICENSES_MAPPING = {
    'None': None,
    'Apache 2.0': 'apache-2.0',
    'Apache License 2.0': 'apache-2.0',
    'Apache-2.0': 'apache-2.0',
    'Apache': 'apache-2.0',
    'GPL': 'gpl-2.0',
    'GPL-2': 'gpl-2.0',
    'GNU GPL v2': 'gpl-2.0',
    'GPLv2+': 'gpl-2.0-plus',
    'GPLv2': 'gpl-2.0',
    'GPLv3': 'gpl-3.0',
    'MIT': 'mit',
    'Ruby': 'ruby',
    "same as ruby's": 'ruby',
    'Ruby 1.8': 'ruby',
    'Artistic 2.0': 'artistic-2.0',
    'Perl Artistic v2': 'artistic-2.0',
    '2-clause BSDL': 'bsd-simplified',
    'BSD': 'bsd-new',
    'BSD-3': 'bsd-new',
    'ISC': 'isc',
    'SIL Open Font License': 'ofl-1.0',
    'New Relic': 'new-relic',
    'GPL2': 'gpl-2.0',
    'BSD-2-Clause': 'bsd-simplified',
    'BSD 2-Clause': 'bsd-simplified',
    'LGPL-3': 'lgpl-3.0',
    'LGPL-2.1+': 'lgpl-2.1-plus',
    'LGPLv2.1+': 'lgpl-2.1-plus',
    'LGPL': 'lgpl',
    'Unlicense': 'unlicense',
}
