#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

import packagedcode.models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.utils import form_vcs_url
from minecode.utils import get_http_response
from minecode.utils import parse_date


class GitlabSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://gitlab.com/api/v4/projects"


@visit_router.route("https://gitlab.com/api/v4/projects")
class GitlabAPIHeaderVisitor(HttpVisitor):
    """
    Get the header of the API, and parse the page size and total pages from the
    header, and yield urls for further visiting like GitlabAPIVisitor
    """

    def fetch(self, uri, timeout=10):
        """Return only the headers of the response."""
        return get_http_response(uri, timeout).headers

    def get_uris(self, content):
        new_page_template = "https://gitlab.com/api/v4/projects?page={next_page}&per_page={per_page}&statistics=true"

        page_size = content.get("X-Per-Page")
        total_pages = content.get("X-Total-Pages")
        if page_size and total_pages:
            total_pages = int(total_pages)
            for i in range(total_pages):
                # Use the loop  to yield the uri of next page of the visitor.
                nextpage_url = new_page_template.format(
                    next_page=i + 1, per_page=page_size
                )
                yield URI(uri=nextpage_url, source_uri=self.uri, visited=False)


@visit_router.route(
    r"https://gitlab.com/api/v4/projects\?page=\d+&per_page=\d+&statistics=true"
)
class GitlabAPIVisitor(HttpJsonVisitor):
    """
    Return URIs from the json content of one API page returned from gitlab api.
    This yields the "web_url" from each package in the current json page.
    """

    def get_uris(self, content):
        """
        Yield URIs from the json content, the passing content is the json info, the example is:
        [
              {
                "id": 6377679,
                ...
                "web_url": "https://gitlab.com/prithajnath/cnn-keras",
                ...
              },
              {
                ..
                  "web_url": "https://gitlab.com/janpoboril/rules-bug",
                ...
             }
            ...
            ]
        Each element in the list is a dictionary, and we concern the web_url for the visitor and also return the data.
        """
        if not content:
            # If the page is empty, just return
            return
        for element in content:
            # The element is one package in the list of current returned page.
            url = element.get("web_url")
            if url:
                project_name = url.rpartition("/")[-1]
                package_url = PackageURL(type="gitlab", name=project_name).to_string()
                yield URI(
                    uri=url,
                    package_url=package_url,
                    data=element,
                    source_uri=self.uri,
                    visited=False,
                )


@map_router.route("https://gitlab.com/.*")
class GitLabMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_json(metadata, resource_uri.package_url)


def build_packages_from_json(metadata, purl=None):
    """
    Yield Package built from gitlab json content
    metadata: Json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    content = json.loads(metadata)

    name = content.get("name")
    if name:
        common_data = dict(
            type="gitlab",
            name=name,
            homepage_url=content.get("web_url"),
            description=content.get("description"),
        )
        repo_url = content.get("http_url_to_repo")
        if repo_url:
            repo_url = form_vcs_url("git", repo_url)
            common_data["vcs_url"] = repo_url
        common_data["code_view_url"] = repo_url
        common_data["release_date"] = parse_date(content.get("created_at"))
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
