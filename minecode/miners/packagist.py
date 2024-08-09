#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode import models as scan_models
from packagedcode.models import DependentPackage
from packageurl import PackageURL

from minecode import seed
from minecode import map_router
from minecode import visit_router
from minecode.miners import Mapper
from minecode.miners import HttpJsonVisitor
from minecode.miners import URI
from minecode.utils import form_vcs_url


"""
Collect packagist packages

The packagist repo API is at: https://packagist.org/apidoc
"""


class PackagistSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://packagist.org/packages/list.json'


@visit_router.route('https://packagist.org/packages/list.json')
class PackagistListVisitor(HttpJsonVisitor):
    """
    Collect list json resource and yield URIs for searching with package url.

    The yield uri format is like: https://packagist.org/p/[vendor]/[package].json
    """

    def get_uris(self, content):
        search_url_template = 'https://packagist.org/p/{vendor}/{package}.json'
        packages_entries = content.get('packageNames', {})
        for package in packages_entries:
            # FIXME: what does it mean to have no / in the URL?
            if '/' not in package:
                continue
            vp = package.split('/')
            vendor = vp[0]
            package = vp[1]
            package_url = PackageURL(type='composer', name=package).to_string()
            yield URI(uri=search_url_template.format(vendor=vendor, package=package), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://packagist.org/p/.*json')
class PackageVisitor(HttpJsonVisitor):
    """
    Collect JSON for a package.
    """
    # FIXME: what about having a download URL to fetch the real package???
    pass


@map_router.route('https://packagist.org/p/.*json')
class PackagistPackageMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are multiple versions.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_with_json(metadata, resource_uri.package_url, uri)


def build_packages_with_json(metadata, purl=None, uri=None):
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
                datasource_id='php_composer_json',
                type='composer',
                name=version_content.get('name'),
                description=version_content.get('description'),
                primary_language=primary_language,
            )
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
                common['parties'].append(
                    scan_models.Party(name=author.get('name'), role='author', url=author.get(
                        'homepage'), email=author.get('email')).to_dict()
                )

            extracted_license_statement = set([])
            for lic in version_content.get('license'):
                extracted_license_statement.add(lic)
            if extracted_license_statement:
                common['extracted_license_statement'] = list(
                    extracted_license_statement)
                common['license_detections'] = []

            dependencies = []
            for name, version in version_content.get('require', {}).items():
                dependencies.append(
                    DependentPackage(
                        purl=name, extracted_requirement=version, scope='runtime').to_dict()
                )
            if dependencies:
                common['dependencies'] = dependencies
            # FIXME: We should create a composer package
            package = scan_models.Package.from_package_data(
                package_data=common,
                datafile_path=uri,
            )
            package.set_purl(purl)
            yield package
