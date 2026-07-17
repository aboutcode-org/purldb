#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from bs4 import BeautifulSoup
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.utils import form_vcs_url


class FreedesktopSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://www.freedesktop.org/wiki/Software"


@visit_router.route("https://www.freedesktop.org/wiki/Software")
class FreedesktopHTMLVisitor(HttpVisitor):
    """Visit the Freedesktop Software HTML page and return URIs parsed from HTML page."""

    def get_uris(self, content):
        url_template = "https://www.freedesktop.org/wiki/Software/{name}"
        page = BeautifulSoup(content, "lxml")
        for div in page.find_all(name="div"):
            for a in div.find_all(name="a"):
                if "href" not in a.attrs:
                    continue
                href = a["href"]
                if href and href.startswith("./"):
                    project_name = href.replace("./", "").strip("/")
                    package_url = PackageURL(type="freedesktop", name=project_name).to_string()
                    yield URI(
                        uri=url_template.format(name=project_name),
                        package_url=package_url,
                        source_uri=self.uri,
                    )


@visit_router.route("https://www.freedesktop.org/wiki/Software/.*")
class FreedesktopProjectHTMLVisitor(HttpVisitor):
    """Visit the Freedesktop Project HTML page."""

    pass


@map_router.route("https://www.freedesktop.org/wiki/Software/.*")
class FreedesktopHTMLProjectMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        return build_packages(resource_uri.data, uri, resource_uri.package_url)


def build_packages(html_text, uri, purl):
    """
    Yield Package objects built from `html_text` from the `uri` and the `purl`
    package URL string.
    """
    purl = PackageURL.from_string(purl)
    package_data = dict(type="freedesktop", name=purl.name, version=purl.version, homepage_url=uri)

    page = BeautifulSoup(html_text, "lxml")
    if page.h1:
        package_data["description"] = page.h1.string.strip()

    for a in page.find_all(name="a"):
        link = a["href"]
        if "freedesktop.org" not in link:
            continue

        if "/releases/" in link or "/dist/" in link:
            package_data["download_url"] = link

        if "https://bugs.freedesktop.org/buglist.cgi" in link:
            package_data["bug_tracking_url"] = link

        if "http://cgit.freedesktop.org/" in link and "tree/" in link:
            package_data["code_view_url"] = link

    for li in page.find_all(name="li"):
        if li.text and li.text.startswith("git://"):
            package_data["vcs_url"] = form_vcs_url("git", li.text)

    yield scan_models.Package(**package_data)
