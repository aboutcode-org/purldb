#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import string

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


def get_search_conditions():
    """
    Return a list of combination of char and char, char and number, number and number.
    By doing this, we can pass the conditions to the query API of docker hub, the API does not
    support the single char, so we combine two chars as a list.
    For example: ['aa', 'ab', .....'a1', 'a2'.....'z9'...]
    """
    char_list = []
    for char in string.ascii_lowercase:
        char_list.append(char)
    int_list = []
    for i in range(0, 10):
        int_list.append(str(i))
    char_list.extend(int_list)

    conditions = []
    for c in char_list:
        for second_c in char_list:
            conditions.append(c + second_c)
    return conditions


class DockerHubSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://hub.docker.com/explore/?page=1"
        search_uril_format = (
            "https://index.docker.io/v1/search?q={condition}&n=100&page=1"
        )
        for condition in get_search_conditions():
            # yield a combination of query conditions, the API accepts at least
            # two chars for searching conditions.
            yield search_uril_format.format(condition=condition)


@visit_router.route(r"https://hub.docker.com/explore/\?page=\d?")
class DockHubExplorePageVisitor(HttpVisitor):
    """Visit the HTML page of DockerHub Explore Page and yield each uri of the project, and yield the next page of DockHub."""

    def get_uris(self, content):
        dockhub_library_html_template = "https://hub.docker.com/{project}"
        dockhub_library_restapi_template = (
            "https://registry.hub.docker.com/v2/repositories/library/{project}"
        )
        dockhub_next_page_template = "https://hub.docker.com/explore/?page={page}"
        page_legal = False
        page = BeautifulSoup(content, "lxml")
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue
            href = a["href"]
            if href and href.startswith("/_/"):
                page_legal = True
                project_name = href[1:]
                package_url = PackageURL(
                    type="docker",
                    name=project_name.replace("_/", "library/").rstrip("/"),
                ).to_string()
                yield URI(
                    uri=dockhub_library_html_template.format(project=project_name),
                    package_url=package_url,
                    source_uri=self.uri,
                )
                yield URI(
                    uri=dockhub_library_restapi_template.format(
                        project=href.partition("/_/")[-1]
                    ),
                    package_url=package_url,
                    source_uri=self.uri,
                )
        if page_legal:
            current_page = int(self.uri.partition("=")[-1])
            next_page = current_page + 1
            yield URI(
                uri=dockhub_next_page_template.format(page=next_page),
                source_uri=self.uri,
            )


@visit_router.route(r"https://hub.docker.com/_/[\w\-\.]+/")
class DockHubProjectHTMLVisitor(HttpVisitor):
    def dumps(self, content):
        """Return the json by parsing the HTML project page"""
        metadata_dict = dict()
        page = BeautifulSoup(content, "lxml")
        for div in page.find_all(name="div"):
            for span in div.find_all(name="span"):
                if span.string == "Short Description":
                    next_sibling = div.next_sibling
                    if next_sibling:
                        for sibling_span in next_sibling.find_all(name="span"):
                            sibling_text = sibling_span.string
                            metadata_dict["summary"] = sibling_text
            for h1 in div.find_all(name="h1"):
                if h1.string == "License":
                    licenses_paras = []
                    next_sibling = h1.next_sibling
                    while next_sibling:
                        if next_sibling.string:
                            licenses_paras.append(next_sibling.string)
                        next_sibling = next_sibling.next_sibling
                    if licenses_paras:
                        metadata_dict["license_text"] = "".join(licenses_paras)
        return json.dumps(metadata_dict)


@visit_router.route(
    r"https://registry.hub.docker.com/v2/repositories/library/[\w\-\.]+/"
)
class DockHubLibraryRESTJsonVisitor(HttpJsonVisitor):
    """
    Return URIs by parsing the json content of API of Dock Hub library
    Note that this class is reuse the parent's function to return json data.
    """


@visit_router.route(r"https://index.docker.io/v1/search\?q=\w\w&n=100&page=\d+")
class DockHubGetAllProjectsFromSearchVisitor(HttpJsonVisitor):
    def get_uris(self, content):
        base_url = "https://hub.docker.com/v2/repositories/{name}"
        num_page = content.get("num_pages")
        current_page = content.get("page")
        if num_page and current_page:
            if int(current_page) < int(num_page):
                next_page = int(current_page) + 1
                yield URI(
                    uri=(self.uri.rpartition("=")[0] + "=" + str(next_page)),
                    source_uri=self.uri,
                )
        results = content.get("results", {})
        for result in results:
            name = result.get("name")
            # TODO: This will be used when new Package definition is merged.
            star_count = result.get("star_count")
            if name:
                package_url = PackageURL(type="docker", name=name).to_string()
                yield URI(
                    uri=base_url.format(name=name),
                    package_url=package_url,
                    source_uri=self.uri,
                )


@map_router.route(r"https://registry.hub.docker.com/v2/repositories/library/[\w\-\.]+/")
class DockerHubLiraryJsonMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_jsonfile(
            metadata, resource_uri.uri, resource_uri.package_url
        )


def build_packages_from_jsonfile(metadata, uri=None, purl=None):
    """
    Yield Package built from Docker Hub json content.
    metadata: json metadata content
    uri: String value of uri of the ResourceURI object.
    purl: String value of the package url of the ResourceURI object
    """
    content = json.loads(metadata)
    dockhub_library_htmlpage_template = "https://hub.docker.com/_/{project}"
    name = content.get("name")
    if name:
        short_desc = content.get("description")
        long_desc = content.get("full_description")
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = "\n".join(descriptions)
        common_data = dict(
            type="docker",
            name=name,
            description=description,
            homepage_url=dockhub_library_htmlpage_template.format(project=name),
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
