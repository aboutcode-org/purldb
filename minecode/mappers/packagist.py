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
from packagedcode.models import DependentPackage

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import form_vcs_url


@map_router.route('https://packagist.org/p/.*json')
class PackagistPackageMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are multiple versions.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_with_json(metadata, resource_uri.package_url)


def build_packages_with_json(metadata, purl=None):
    """
    Yield Package built from Packist package json content.
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """

    package = metadata.get('package')
    if package:
        primary_language = package.get('language')
        for version_content in package.get('versions').values():
            common = dict(
                type='composer',
                name=version_content.get('name'),
                description=version_content.get('description'),
                primary_language=primary_language)
            common['version'] = version_content.get('version')
            common['keywords'] = version_content.get('keywords')
            common['homepage_url'] = version_content.get('homepage')

            source = version_content.get('source')
            if source:
                if source.get('type') == 'git' and source.get('url'):
                    common['vcs_url'] = form_vcs_url('git', source.get('url'))
                else:
                    pass  # Packagist only has the github repo

            dist = version_content.get('dist')
            if dist:
                common['download_url'] = dist.get('url')
                common['sha1'] = dist.get('shasum')

            for author in version_content.get('authors', []):
                parties = common.get('parties')
                if not parties:
                    common['parties'] = []
                common['parties'].append(scan_models.Party(name=author.get('name'), role='author', url=author.get('homepage'), email=author.get('email')))

            extracted_license_statement = set([])
            for lic in version_content.get('license'):
                extracted_license_statement.add(lic)
            if extracted_license_statement:
                common['extracted_license_statement'] = list(extracted_license_statement)

            dependencies = []
            for name, version in version_content.get('require', {}).items():
                dependencies.append(
                    DependentPackage(purl=name, extracted_requirement=version, scope='runtime')
                )
            if dependencies:
                common['dependencies'] = dependencies
            # FIXME: We should create a composer package
            package = scan_models.Package(**common)
            package.set_purl(purl)
            yield package
