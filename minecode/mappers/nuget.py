#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from bs4 import BeautifulSoup

from packagedcode import models as scan_models

from minecode import map_router
from minecode.mappers import Mapper


@map_router.route('https://api.nuget.org/v3/catalog.+\.json')
class NugetPackageMapper(Mapper):
    """
    Return NugetPackage object by parsing the ResourceURI stored in db referenced by the
    nuget API URIs.
    """

    def get_packages(self, uri, resource_uri):
        if not resource_uri.data:
            return
        pkg_data = json.loads(resource_uri.data)
        return build_packages_with_json(pkg_data, resource_uri.package_url)


def build_packages_with_json(metadata, purl=None):
    """
    Yield package from the json metadata passed
    metadata: json metadata content from API call
    purl: String value of the package url of the ResourceURI object
    """
    licenseUrl = metadata.get('licenseUrl')
    copyr = metadata.get('copyright')

    authors = []
    names = metadata.get('authors')
    if names:
        for name in names.split(','):
            authors.append(scan_models.Party(name=name.strip(), role='author'))

    keywords = metadata.get('tags', [])

    # TODO: the content has the SHA512, our model may extend to SHA512

    if name:
        short_desc = metadata.get('summary')
        long_desc = metadata.get('description')
        if long_desc == short_desc:
            long_desc = None
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = '\n'.join(descriptions)
        package_mapping = dict(
            type='nuget',
            name=metadata['id'],
            version=metadata['version'],
            homepage_url=metadata.get('projectUrl'),
            description=description,
            extracted_license_statement=licenseUrl,
            license_detections=[],
            copyright=copyr,
            parties=authors,
            keywords=keywords,
        )
        package = scan_models.PackageData.from_data(
            package_data=package_mapping)
        package.set_purl(purl)
        yield package


@map_router.route('https://api.nuget.org/packages/.*\.nupkg')
class NugetNUPKGDownloadMapper(Mapper):
    """
    Return NugetPackage object by parsing the download URL.
    For example: https://api.nuget.org/packages/entityframework.4.3.1.nupkg
    """

    def get_packages(self, uri, resource_uri):
        if not resource_uri.data:
            return
        pkg_data = json.loads(resource_uri.data)
        return build_packages_with_nupkg_download_url(pkg_data, resource_uri.package_url, resource_uri.uri)


def build_packages_with_nupkg_download_url(metadata, purl, uri):
    if purl:
        package = scan_models.PackageData(
            type='nuget',
            name=purl.name,
            download_url=uri
        )
        package.set_purl(purl)
        yield package


@map_router.route('https://www.nuget.org/packages/[\w\-\.]+',
                  'https://www.nuget.org/packages/[\w\-\.]+/[\w\-\.]+')
class NugetHTMLPackageMapper(Mapper):
    """
    Return NugetPackage object by parsing the package HTML content.
    For example:  https://www.nuget.org/packages/log4net
    """

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri data.
        """
        metadata = resource_uri.data
        build_packages_from_html(
            metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_html(metadata, uri, purl=None):
    """
    Yield Package built from Nuget a `metadata` content
    metadata: json metadata content
    uri: the uri of the ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    download_url_format = 'https://www.nuget.org/api/v2/package/{name}/{version}'
    soup = BeautifulSoup(metadata, 'lxml')
    h1 = soup.find('h1')
    if h1 and h1.contents:
        license_value = None
        name = str(h1.contents[0]).strip()
        for a in soup.find_all('a'):
            if a.get('data-track') and a.get('data-track') == 'outbound-license-url':
                license_value = a.string
                if license_value:
                    license_value = str(license_value).strip()

        copyright_value = None
        h2s = soup.find_all('h2')
        for h2 in h2s:
            # Copyright will be after the copyright h2 node
            # The exmaple is like this:
            #        <h2>Copyright</h2>
            #        <p>Copyright 2004-2017 The Apache Software Foundation</p>
            if h2.string and h2.string == 'Copyright':
                next_element = h2.find_next_sibling('p')
                if next_element:
                    copyright_value = next_element.string

        description = None
        for m in soup.find_all('meta'):
            if m.get('property') and m.get('property') == 'og:description' and m.get('content'):
                description = m.get('content')

        for tbody in soup.find_all('tbody'):
            if tbody.get('class') and tbody.get('class')[0] == 'no-border':
                for a in tbody.find_all('a'):
                    version = a.string
                    if not version or not version.strip():
                        continue
                    version = version.strip()
                    download_url = download_url_format.format(
                        name=name, version=version)
                    package_mapping = dict(
                        datasource_id="nuget_metadata_json",
                        name=name,
                        type='nuget',
                        version=version,
                        homepage_url=uri,
                        description=description,
                        download_url=download_url,
                        extracted_license_statement=license_value,
                        license_detections=[],
                        copyright=copyright_value
                    )
                    package = scan_models.Package.from_package_data(
                        package_data=package_mapping,
                        datafile_path=uri,
                    )
                    package.set_purl(purl)
                    yield package
