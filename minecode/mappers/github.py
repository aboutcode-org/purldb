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
from collections import OrderedDict

import attr
import packagedcode.models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import form_vcs_url
from minecode.utils import parse_date

logger = logging.getLogger(__name__)


@map_router.route(r"https://api\.github\.com/repos/([^/]+)/([^/]+)")
class GithubMetaFileMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        visited_data = resource_uri.data
        if not visited_data:
            return
        return build_github_packages(
            visited_data, resource_uri.uri, resource_uri.package_url
        )


def build_github_packages(visited_data, uri, purl=None):
    """
    Yield Package built from Github API visited_data as a JSON string.
    metadata: HTML metadata content
    uri: String value of the uri from ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    visited_data = json.loads(visited_data, object_pairs_hook=OrderedDict)

    full_name = visited_data["full_name"]
    namespace, name = split_org_repo(full_name)
    # FIXME: when could this ever happen??
    assert name == visited_data["name"], (
        "build_github_packages: Inconsistent name and org for URI: " + uri
    )

    description = visited_data["description"]

    vcs_url = (visited_data.get("git_url"),)
    if vcs_url:
        vcs_url = form_vcs_url("git", vcs_url)
    package = scan_models.Package(
        type="github",
        namespace=namespace,
        name=name,
        description=description,
        primary_language=visited_data.get("language"),
        homepage_url=visited_data.get("html_url"),
        vcs_url=vcs_url,
        # this size does not make sense
        size=visited_data.get("size"),
    )

    if visited_data.get("owner"):
        package.parties = [
            scan_models.Party(
                # FIXME: we can add the org or user URL and we can know if this
                # is an org or a perrsone too.
                type=scan_models.party_person,
                name=visited_data.get("owner"),
                role="owner",
            )
        ]

    package.set_purl(purl)

    downloads = visited_data.get("downloads") or []
    for download in downloads:
        html_url = download.get("html_url")
        if html_url:
            # make a copy
            package = attr.evolve(package)
            package.download_url = html_url
            package.size = download.get("size")
            package.release_date = parse_date(download.get("created_at"))
            yield package

    tags = visited_data.get("tags") or []
    for tag in tags:
        package = attr.evolve(package)
        package.version = tag.get("name")
        package_url = PackageURL(
            type="github",
            name=package.name,
            namespace=namespace,
            version=tag.get("name"),
        ).to_string()
        package.sha1 = tag.get("sha1")
        if tag.get("tarball_url"):
            package.download_url = tag.get("tarball_url")
            package.set_purl(package_url)
            yield package
        if tag.get("zipball_url"):
            package.download_url = tag.get("zipball_url")
            package.set_purl(package_url)
            yield package

    branches_download_urls = visited_data.get("branches_download_urls") or []
    for branches_download_url in branches_download_urls:
        package = attr.evolve(package)
        package.download_url = branches_download_url
        yield package


def split_org_repo(url_like):
    """
    Given a URL-like string to a GitHub repo or a repo name as in org/name,
    split and return the org and name.

    For example:
    >>> split_org_repo('foo/bar')
    ('foo', 'bar')
    >>> split_org_repo('https://api.github.com/repos/foo/bar/')
    ('foo', 'bar')
    >>> split_org_repo('github.com/foo/bar/')
    ('foo', 'bar')
    >>> split_org_repo('git://github.com/foo/bar.git')
    ('foo', 'bar')
    """
    segments = [s.strip() for s in url_like.split("/") if s.strip()]
    if not len(segments) >= 2:
        raise ValueError(f"Not a GitHub-like URL: {url_like}")
    org = segments[-2]
    name = segments[-1]
    if name.endswith(".git"):
        name, _, _ = name.rpartition(".git")
    return org, name
