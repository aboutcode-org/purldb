#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from bs4 import BeautifulSoup
from commoncode import fileutils
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import HttpVisitor
from minecode.miners import Mapper


class NugetSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://api-v2v3search-0.nuget.org/query"
        yield "https://www.nuget.org/packages?page=1"


@visit_router.route("https://api-v2v3search-0.nuget.org/query")
class NugetQueryVisitor(HttpJsonVisitor):
    """
    'https://api-v2v3search-0.nuget.org/query' is a query URL which has metadata for
    Nuget packages and we can query for all the packages by using the pagination
    technique. For example 'https://api-v2v3search-0.nuget.org/query?skip=40' will
    skip the first 40 packages in the order and returns JSON data for the packages
    from 40-60.
    'https://api-v2v3search-0.nuget.org/query' could be the latest version, as the
    url 'https://api-v3search-0.nuget.org/query' is not accessible now.
    """

    def get_uris(self, content):
        """
        Return all the URLs for query results through pagination.
        Starts with number '0', increment count by '20'.
        The total count is found by 'totalHits'.
        """
        pkgs_count = content.get("totalHits", 0)
        count = 0
        url_template = "https://api-v2v3search-0.nuget.org/query?skip={count}"
        while count < pkgs_count:
            url = url_template.format(count=str(count))
            yield URI(uri=url, source_uri=self.uri)
            count = count + 20


@visit_router.route(r"https://api-v2v3search-0.nuget.org/query\?skip=\d+")
class PackagesPageVisitor(HttpJsonVisitor):
    """Visit the nuget API resources and return all the package URLs available at the passing`uri`."""

    def get_uris(self, content):
        metadata = content["data"]
        for packages in metadata:
            for version in packages["versions"]:
                pkg_ver = version["version"]
                pkg_url = version["@id"]
                version_template = "{pkg_version}.0.json"
                version_name = version_template.format(pkg_version=pkg_ver)
                name = pkg_url.replace(
                    "https://api.nuget.org/v3/registration1/", ""
                ).partition("/")[0]
                package_url = PackageURL(
                    type="nuget", name=name, version=pkg_ver
                ).to_string()
                if version_name in pkg_url:
                    # sometimes an extra '0' is appended to the version in the URL
                    # FIXME: this is weird: there must be good reason why this is done???
                    pkg_url = pkg_url.replace(version_name, pkg_ver + ".json")
                yield URI(uri=pkg_url, package_url=package_url, source_uri=self.uri)

                # Add another case to have registration0 or registration1 in the url, yield the alternative url.
                if pkg_url.find("/registration0/") > 0:
                    pkg_url = pkg_url.replace("/registration0/", "/registration1/")
                    yield URI(uri=pkg_url, source_uri=self.uri)

                elif pkg_url.find("/registration1/") > 0:
                    pkg_url = pkg_url.replace("/registration1/", "/registration0/")
                    yield URI(uri=pkg_url, source_uri=self.uri)


@visit_router.route("https://api.nuget.org/.+.json")
class NugetAPIJsonVisitor(HttpJsonVisitor):
    """
    Visit packageContent of nuget API json  and return a
    download URL for the NugetPackage object

    This could cover three cases:
    1. packageContent is not empty.
    https://api.nuget.org/v3/registration1/entityframework/4.3.1.json
    Visiting above link will return the npkg file: https://api.nuget.org/packages/entityframework.4.3.1.nupkg
     and return the json resource for next DownloadVisitor: https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json

    2. catalogEntry is not empty
    https://api.nuget.org/v3/registration1/entityframework/4.3.1.json
    Visiting above link will return the npkg file: https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json

    3. No key matched
    The second loop will return the url https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json
    by visiting this url it won't create any new uris, the key is to store the json file itself through visitor and used in mapper.
    """

    def get_uris(self, content):
        download_url = content.get("packageContent")
        if download_url:
            filename = fileutils.file_name(download_url)
            withou_prefix = filename.replace(".nupkg", "")
            filename_splits = withou_prefix.partition(".")
            name = filename_splits[0]
            version = None
            if len(filename_splits) > 1:
                version = filename_splits[-1]
            package_url = PackageURL(type="nuget", name=name, version=version)
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)

        catalog_entry_url = content.get("catalogEntry")
        if catalog_entry_url:
            yield URI(uri=catalog_entry_url, source_uri=self.uri)


@visit_router.route(r"https://www.nuget.org/packages\?page=\d+")
class NugetHTMLPageVisitor(HttpVisitor):
    """Visitor to yield the URI of the each package page."""

    def get_uris(self, content):
        url_format = "https://www.nuget.org/packages/{name}"
        soup = BeautifulSoup(content, "lxml")
        has_package = False
        for a in soup.find_all("a"):
            if a.get("class") and "package-title" in a.get("class"):
                has_package = True
                href = a.get("href")
                if not href:
                    continue
                # href format is like: "/packages/NUnit/"
                name = href.strip("/").partition("/")[-1]
                if name:
                    yield URI(uri=url_format.format(name=name), source_uri=self.uri)
        if has_package:
            page_id = self.uri.replace(
                "https://www.nuget.org/packages?page=", ""
            ).strip("/")
            next_pageid = int(page_id) + 1
            nextpage_url_format = "https://www.nuget.org/packages?page={id}"
            yield URI(
                uri=nextpage_url_format.format(id=next_pageid), source_uri=self.uri
            )


@visit_router.route(
    r"https://www.nuget.org/packages/[\w\-\.]+",
    r"https://www.nuget.org/packages/[\w\-\.]+/[\w\-\.]+",
)
class NugetHTMLPackageVisitor(HttpVisitor):
    """
    Visitor to fetch the package HTML content
    Example: https://www.nuget.org/packages/log4net
             or https://www.nuget.org/packages/log4net/2.0.7
    """

    pass


@map_router.route(r"https://api.nuget.org/v3/catalog.+\.json")
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
    licenseUrl = metadata.get("licenseUrl")
    copyr = metadata.get("copyright")

    authors = []
    names = metadata.get("authors")
    if names:
        for name in names.split(","):
            authors.append(scan_models.Party(name=name.strip(), role="author"))

    keywords = metadata.get("tags", [])

    # TODO: the content has the SHA512, our model may extend to SHA512

    if name:
        short_desc = metadata.get("summary")
        long_desc = metadata.get("description")
        if long_desc == short_desc:
            long_desc = None
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = "\n".join(descriptions)
        package_mapping = dict(
            type="nuget",
            name=metadata["id"],
            version=metadata["version"],
            homepage_url=metadata.get("projectUrl"),
            description=description,
            extracted_license_statement=licenseUrl,
            license_detections=[],
            copyright=copyr,
            parties=authors,
            keywords=keywords,
            declared_license_expression=metadata.get("licenseExpression"),
            download_url=metadata.get("packageContent"),
        )
        package = scan_models.PackageData.from_data(package_data=package_mapping)
        package.set_purl(purl)
        yield package


@map_router.route(r"https://api.nuget.org/packages/.*\.nupkg")
class NugetNUPKGDownloadMapper(Mapper):
    """
    Return NugetPackage object by parsing the download URL.
    For example: https://api.nuget.org/packages/entityframework.4.3.1.nupkg
    """

    def get_packages(self, uri, resource_uri):
        if not resource_uri.data:
            return
        pkg_data = json.loads(resource_uri.data)
        return build_packages_with_nupkg_download_url(
            pkg_data, resource_uri.package_url, resource_uri.uri
        )


def build_packages_with_nupkg_download_url(metadata, purl, uri):
    if purl:
        package = scan_models.PackageData(
            type="nuget", name=purl.name, download_url=uri
        )
        package.set_purl(purl)
        yield package


@map_router.route(
    r"https://www.nuget.org/packages/[\w\-\.]+",
    r"https://www.nuget.org/packages/[\w\-\.]+/[\w\-\.]+",
)
class NugetHTMLPackageMapper(Mapper):
    """
    Return NugetPackage object by parsing the package HTML content.
    For example:  https://www.nuget.org/packages/log4net
    """

    def get_packages(self, uri, resource_uri):
        """Yield Package built from resource_uri data."""
        metadata = resource_uri.data
        build_packages_from_html(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_html(metadata, uri, purl=None):
    """
    Yield Package built from Nuget a `metadata` content
    metadata: json metadata content
    uri: the uri of the ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    download_url_format = "https://www.nuget.org/api/v2/package/{name}/{version}"
    soup = BeautifulSoup(metadata, "lxml")
    h1 = soup.find("h1")
    if h1 and h1.contents:
        license_value = None
        name = str(h1.contents[0]).strip()
        for a in soup.find_all("a"):
            if a.get("data-track") and a.get("data-track") == "outbound-license-url":
                license_value = a.string
                if license_value:
                    license_value = str(license_value).strip()

        copyright_value = None
        h2s = soup.find_all("h2")
        for h2 in h2s:
            # Copyright will be after the copyright h2 node
            # The exmaple is like this:
            #        <h2>Copyright</h2>
            #        <p>Copyright 2004-2017 The Apache Software Foundation</p>
            if h2.string and h2.string == "Copyright":
                next_element = h2.find_next_sibling("p")
                if next_element:
                    copyright_value = next_element.string

        description = None
        for m in soup.find_all("meta"):
            if (
                m.get("property")
                and m.get("property") == "og:description"
                and m.get("content")
            ):
                description = m.get("content")

        for tbody in soup.find_all("tbody"):
            if tbody.get("class") and tbody.get("class")[0] == "no-border":
                for a in tbody.find_all("a"):
                    version = a.string
                    if not version or not version.strip():
                        continue
                    version = version.strip()
                    download_url = download_url_format.format(
                        name=name, version=version
                    )
                    package_mapping = dict(
                        datasource_id="nuget_metadata_json",
                        name=name,
                        type="nuget",
                        version=version,
                        homepage_url=uri,
                        description=description,
                        download_url=download_url,
                        extracted_license_statement=license_value,
                        license_detections=[],
                        copyright=copyright_value,
                    )
                    package = scan_models.Package.from_package_data(
                        package_data=package_mapping,
                        datafile_path=uri,
                    )
                    package.set_purl(purl)
                    yield package
