#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import packagedcode.models as scan_models
from bs4 import BeautifulSoup
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.utils import parse_date

CRAN_URL = "https://cloud.r-project.org/"
CRAN_WEB_URL = CRAN_URL + "web/"


class CranSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://cloud.r-project.org/web/packages/available_packages_by_date.html"


@visit_router.route(
    "https://cloud.r-project.org/web/packages/available_packages_by_date.html"
)
class CranPackagesVisitors(HttpVisitor):
    """Return URIs by parsing the HTML content of the page"""

    def get_uris(self, content):
        base_url = "https://cloud.r-project.org/web/packages/{package}/index.html"
        a_blocks = BeautifulSoup(content, "lxml").find_all("a")
        for a in a_blocks:
            package = a.text
            package_url = PackageURL(type="cran", name=package).to_string()
            yield URI(
                uri=base_url.format(package=package),
                package_url=package_url,
                source_uri=self.uri,
            )


@visit_router.route(r"https://cloud.r-project.org/web/packages/[\w\-\.]/index.html")
class CranSinglePackageVisitor(HttpVisitor):
    """Return only the HTML content of the page, and will be parsed in mapper"""

    pass


@map_router.route(r"https://cloud.r-project.org/web/packages/[\w\-\.]/index.html")
class CranMetaFileMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_html(metadata, resource_uri.uri, resource_uri.package_url)


def get_download_url(url):
    return url.replace("../../../", CRAN_URL)


def get_dependencies(depends):
    """Return a dictionary of dependencies keyed by dep_group."""
    dep_pkgs = []
    if not depends:
        return dep_pkgs
    dependencies = comma_separated(depends)
    if not dependencies:
        return dep_pkgs
    for name in dependencies:
        dep_pkgs.append(scan_models.DependentPackage(purl=name).to_dict())
    return dep_pkgs


def comma_separated(text):
    """Return a list of strings from a comma-separated text."""
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t and t.strip()]


def build_packages_from_html(metadata, uri=None, purl=None):
    """
    Yield Package built from Cpan a `metadata` content
    metadata: json metadata content
    uri: the uri of the ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    # Parse the name from the url, for example: https://cloud.r-project.org/web/packages/ANN2/index.html
    common_data = dict(
        datasource_id="cran_metadata",
        type="cran",
        name=uri.rpartition("/")[0].rpartition("/")[-1],
    )
    extracted_license_statement = []
    download_urls = []

    soup = BeautifulSoup(metadata, "lxml")
    first_pblock = soup.find("p")
    if first_pblock:
        common_data["description"] = first_pblock.string
    else:
        h2_block = soup.find("h2")
        if h2_block:
            common_data["description"] = h2_block.string

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            col_values = []
            cols = row.find_all("td")
            for ele in cols:
                if ele.find_all("a"):
                    col_values.append([a["href"].strip() for a in ele.find_all("a")])
                col_values.append(ele.text.strip())
            if len(cols) >= 2:
                key = col_values[0]
                value = col_values[1]
                if key == "Version:":
                    common_data["version"] = value
                elif key == "URL:":
                    if type(value) is list and len(value) > 0:
                        homepages = []
                        for home_page in value:
                            homepages.append(home_page)
                        common_data["homepage_url"] = "\n".join(homepages)
                    else:
                        common_data["homepage_url"] = value
                elif key == "License:":
                    for license_url in value:
                        extracted_license_statement.append(license_url)
                elif key == "Author:":
                    parties = common_data.get("parties")
                    if not parties:
                        common_data["parties"] = []
                    party = scan_models.Party(
                        type=scan_models.party_person, name=value, role="author"
                    )
                    common_data["parties"].append(party.to_dict())
                elif key == "Maintainer:":
                    maintainer_split = value.split("<")
                    if len(maintainer_split) > 1:
                        parties = common_data.get("parties")
                        if not parties:
                            common_data["parties"] = []
                        party = scan_models.Party(
                            type=scan_models.party_person,
                            name=maintainer_split[0].rstrip(),
                            role="maintainer",
                            email=maintainer_split[1]
                            .replace(">", "")
                            .replace(" at ", "@"),
                        )
                        common_data["parties"].append(party.to_dict())
                elif "source" in key or "binaries" in key:
                    if type(value) is list:
                        for url in value:
                            download_urls.append(get_download_url(url))
                elif key == "Published:":
                    common_data["release_date"] = parse_date(value)
                elif key == "Imports:":
                    # use the text instead of a href since the text is more accurate
                    if len(col_values) == 3:
                        value = col_values[2]
                    common_data["dependencies"] = get_dependencies(value)
    if extracted_license_statement:
        common_data["extracted_license_statement"] = extracted_license_statement
        common_data["license_detections"] = []

    if download_urls:  # for else statement will have else running always if there is no break statement
        for download_url in download_urls:
            package = scan_models.Package.from_package_data(
                package_data=common_data,
                datafile_path=uri,
            )
            package.download_url = download_url
            package.set_purl(purl)
            yield package
    else:
        # Yield a package without download_url
        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package.set_purl(purl)
        yield package
