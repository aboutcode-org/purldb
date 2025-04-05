#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging
import re

from bs4 import BeautifulSoup
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.miners import NonPersistentHttpVisitor

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class SourceforgeSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://sourceforge.net/sitemap.xml"


@visit_router.route("https?://sourceforge.net/sitemap.xml")
class SourceforgeSitemapIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect sub-sitemaps from the main sitemap. Return on URI for each sub-
    sitemap, for example: https://sourceforge.net/sitemap-167.xml

    Note that the class implements from NonPersistentHttpVisitor instead of HttpVisitor,
    as the XML file itself will be over 100M big, so NonPersistentHttpVisitor will be more
    reasonable.
    """

    def get_uris(self, content):
        """Collect all the sitemaps URIs from master sitemap."""
        locs = BeautifulSoup(open(content), "lxml").find_all("loc")
        # Content passing from NonPersistentHttpVisitor is a temp file path
        # instead of file content, so opening to get a file handler is
        # necessary.
        for loc in locs:
            yield URI(uri=loc.text, source_uri=self.uri)


@visit_router.route(r"https?://sourceforge.net/sitemap-\d+.xml")
class SourceforgeSitemapPageVisitor(HttpVisitor):
    def get_uris(self, content):
        """Collect all the projects URIs from a sub-sitemaps."""
        sitemap_locs = BeautifulSoup(content, "lxml").find_all("loc")
        regex = re.compile(r"^https?://sourceforge.net/projects/[a-z0-9.-]+/?$")
        for loc in sitemap_locs:
            if loc.text and re.match(regex, loc.text):
                project_json_baseurl = "https://sourceforge.net/api/project/name/{}/json"
                project_name = loc.text.partition("https://sourceforge.net/projects/")[-1].strip(
                    "/"
                )
                project_json_url = project_json_baseurl.format(project_name)
                package_url = PackageURL(type="sourceforge", name=project_name).to_string()
                # The priority in the xml has different view with the priority in visitor, so skip it.
                yield URI(uri=project_json_url, package_url=package_url, source_uri=self.uri)


@visit_router.route(
    "https?://sourceforge.net/api/project/name/[a-z0-9.-]+/json",
    "https?://sourceforge.net/rest/p/[a-z0-9.-]+",
)
class SourceforgeProjectJsonVisitor(HttpJsonVisitor):
    """
    Collect Sourceforge project data through the JSON API.
    The implementation is empty since it will inherit the implementation from HttpJsonVisitor and it returns json data for mapper.
    """

    pass


@map_router.route(
    "https?://sourceforge.net/api/project/name/[a-z0-9.-]+/json",
    "https?://sourceforge.net/rest/p/[a-z0-9.-]+",
)
class SourceforgeProjectJsonAPIMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_from_metafile(metadata, resource_uri.package_url, uri)


def build_packages_from_metafile(metadata, purl=None, uri=None):
    """
    Yield Package built from package a `metadata` content
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    short_desc = metadata.get("summary")
    long_desc = metadata.get("short_description")
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = "\n".join(descriptions)
    name = metadata.get("shortname")
    # short name is more reasonable here for name, since it's an abbreviation
    # for the project and unique
    if not name:
        name = metadata.get("name")
    if name:
        common_data = dict(
            datasource_id="sourceforge_metadata",
            type="sourceforge",
            name=metadata.get("shortname", metadata.get("name")),
            description=description,
            homepage_url=metadata.get("external_homepage", metadata.get("url")),
            license_detections=[],
        )

        devs = metadata.get("developers") or []
        for dev in devs:
            parties = common_data.get("parties")
            if not parties:
                common_data["parties"] = []
            if dev.get("name"):
                common_data["parties"].append(
                    scan_models.Party(
                        name=dev.get("name"), role="contributor", url=dev.get("url")
                    ).to_dict()
                )

        categories = metadata.get("categories", {})
        languages = categories.get("language", [])
        langs = []
        for lang in languages:
            lshort = lang.get("shortname")
            if lshort:
                langs.append(lshort)
        langs = ", ".join(langs)
        common_data["primary_language"] = langs or None

        extracted_license_statement = []
        licenses = categories.get("license") or []
        for lic in licenses:
            license_name = lic.get("fullname")
            # full name is first priority than shortname since shortname is like gpl, it doesn't show detailed gpl version etc.
            if license_name:
                extracted_license_statement.append(lic.get("shortname"))
            if license_name:
                extracted_license_statement.append(license_name)
        if extracted_license_statement:
            common_data["extracted_license_statement"] = extracted_license_statement

        keywords = []
        topics = categories.get("topic", [])
        for topic in topics:
            keywords.append(topic.get("shortname"))
        common_data["keywords"] = keywords or None
        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package.set_purl(purl)
        yield package
