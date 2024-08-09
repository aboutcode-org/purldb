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

# FIXME: we should create packages from releases!!!! not from projects


@map_router.route('http://projects.eclipse.org/json/project/.*')
class EclipseJsonPackageMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        # FIXME: JSON deserialization should be handled eventually by the framework
        metadata = json.loads(resource_uri.data)
        return build_packages_with_json(metadata, resource_uri.package_url, uri)


def build_packages_with_json(metadata, purl=None, uri=None):
    """
    Yield Package built from Eclipse a `metadata` mapping
    The package can contain multiple projects, and each project can contain
    meta data including title, description, homepage, bug tracking url etc.
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """

    projects = metadata['projects']
    for project, project_metadata in projects.items():
        common_data = dict(
            datasource_id="eclipse_metadata",
            type='eclipse',
            name=project,
        )

        descriptions = project_metadata.get('description')
        if descriptions and len(descriptions) > 0:
            common_data['description'] = descriptions[0].get('value')
        else:
            common_data['description'] = project_metadata['title']

        homepage_urls = project_metadata.get('website_url')
        if homepage_urls and len(homepage_urls) > 0:
            common_data['homepage_url'] = homepage_urls[0].get('url')

        bug_tracking_urls = project_metadata.get('bugzilla')
        if bug_tracking_urls and len(bug_tracking_urls) > 0:
            common_data['bug_tracking_url'] = bug_tracking_urls[0].get(
                'query_url')

        if project_metadata.get('licenses'):
            common_data['extracted_license_statement'] = [
                l.get('name') for l in project_metadata.get('licenses', [])]
            common_data['license_detections'] = []

        # FIXME: this is a download page and NOT a download URL!!!!!
        for download_url in project_metadata.get('download_url', []):
            durl = download_url.get('url')
            if durl:
                common_data['download_url'] = durl
                package = scan_models.Package.from_package_data(
                    package_data=common_data,
                    datafile_path=uri,
                )
                package.set_purl(purl)
                yield package


@map_router.route('https://projects.eclipse.org/projects/.*')
class EclipseHTMLProjectMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        # FIXME: JSON deserialization should be handled eventually by the framework
        return build_packages(resource_uri.data, resource_uri.package_url, uri)


def build_packages(html_text, purl=None, uri=None):
    """
    Yield Package objects built from `html_text`and the `purl` package URL
    string.
    """
    page = BeautifulSoup(html_text, 'lxml')
    common_data = dict(
        datasource_id="eclipse_html",
        type='eclipse',
    )

    extracted_license_statement = []
    for meta in page.find_all(name='meta'):
        if 'name' in meta.attrs and 'dcterms.title' in meta.attrs.get('name'):
            common_data['name'] = meta.attrs.get('content')
        if 'name' in meta.attrs and 'dcterms.description' in meta.attrs.get('name'):
            common_data['description'] = meta.attrs.get('content')

    for div in page.find_all(name='div'):
        if 'class' not in div.attrs:
            continue
        if 'field-name-field-project-licenses' in div.attrs.get('class'):
            # Visit div element whose class atttribute is field-name-field-project-licenses
            for a in div.find_all(name='a'):
                if 'href' not in a.attrs:
                    continue
                license_name = str(a.contents[0])
                extracted_license_statement.append(license_name)
    if extracted_license_statement:
        common_data['extracted_license_statement'] = extracted_license_statement
        common_data['license_detections'] = []

    for a in page.find_all(name='a'):
        if a.contents:
            if str(a.contents[0]).strip() == 'Website':
                common_data['homepage_url'] = a['href']

    for a in page.find_all(name='a'):
        if not a.contents:
            continue
        if str(a.contents[0]).strip() == 'Downloads':
            download_data = dict(download_url=a['href'],)
            download_data.update(common_data)
            package = scan_models.Package.from_package_data(
                package_data=download_data,
                datafile_path=uri,
            )
            package.set_purl(purl)
            yield package

    for div in page.find_all(name='div'):
        if 'class' not in div.attrs:
            continue
        if 'field-name-field-latest-releases' not in div.attrs.get('class'):
            continue
        # Visit div element whose class attribute is ield-name-field-latest-releases
        tbody = div.find(name='tbody')
        if not tbody:
            continue

        for tr in tbody.find_all(name='tr'):
            for td in tr.find_all(name='td'):
                a = td.find(name='a')
                if not a:
                    continue

                if 'href' not in a.attrs or 'class' in a.attrs:
                    continue

                version = a.contents[0]
                href = a['href']
                download_data = dict(
                    version=version,
                    download_url=href,
                )
                download_data.update(common_data)
                package = scan_models.Package.from_package_data(
                    package_data=download_data,
                    datafile_path=uri,
                )
                package.set_purl(purl)
                yield package
