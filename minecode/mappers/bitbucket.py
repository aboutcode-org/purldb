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

from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode.mappers import Mapper

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@map_router.route(
    r"https://api.bitbucket\.org/2\.0/repositories/.*/downloads/",
)
class BitbucketDownloadMapper(Mapper):
    """Build package from download urls if present."""

    def get_packages(self, uri, resource_uri):
        """Yield Package built from resource_uri record for a single package version."""
        downloads_data = json.loads(resource_uri.data, object_pairs_hook=OrderedDict)
        for download_data in downloads_data.get("values", []):
            yield from build_bitbucket_download_packages(
                download_data, resource_uri.package_url
            )


def build_bitbucket_download_packages(download_data, purl):
    """
    Yield scanned Packages for each download
        https://api.bitbucket.org/2.0/repositories/pypa/setuptools/downloads/
    """
    purl = PackageURL.from_string(purl)
    namespace = purl.namespace
    name = purl.name

    # FIXME: add these ?
    # filename = download_data.get("name")
    # download_counts = download_data.get("downloads", 0)

    download_url = download_data.get("links", {}).get("self", {}).get("href")
    size = download_data.get("size")

    package = scan_models.Package(
        type="bitbucket",
        name=name,
        namespace=namespace,
        download_url=download_url,
        size=size,
    )
    package.set_purl(purl)
    yield package


# @map_router.route('https://api.bitbucket.org/2.0/repositories/[^\/]*/[^\/]*')
class BitbucketIndexMapper(Mapper):
    """Build a Package for a repo."""

    def get_packages(self, uri, resource_uri):
        repo = json.loads(resource_uri.data, object_pairs_hook=OrderedDict)
        if not repo:
            return
        yield build_bitbucket_repo_package(repo, resource_uri.package_url)


# FIXME: disabled as this is for a package template
# @map_router.route('https://api.bitbucket.org/2.0/repositories/[^\/]*/[^\/]*')
class BitbucketRepoMapper(Mapper):
    """Build a Package for a repo."""

    def get_packages(self, uri, resource_uri):
        repo = json.loads(resource_uri.data, object_pairs_hook=OrderedDict)
        if not repo:
            return
        yield build_bitbucket_repo_package(repo, resource_uri.package_url)


def build_bitbucket_repo_package(repo_data, purl):
    """
    Peturn a Package "template" from repository data.
    Notes: this is not version-specific and has no download URL.
    """
    purl = PackageURL.from_string(purl)
    scm_protocol = repo_data.get("scm")
    if not scm_protocol:
        scm_protocol = "git"
    bb_url = "{protocol}+https://bitbucket.org/{namespace}/{name}".format(
        protocol=scm_protocol, **purl.to_dict()
    )

    owner = repo_data.get("owner")
    owner_party = scan_models.Party(
        type=scan_models.party_person,
        name=owner.get("username"),
        role="owner",
        url=owner.get("links", {}).get("html", {}).get("href", {}),
    )

    if repo_data.get("has_issues"):
        bug_tracking_url = bb_url + "/issues"
    else:
        bug_tracking_url = None

    package = scan_models.Package(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        homepage_url=repo_data.get("website") or bb_url,
        code_view_url=bb_url + "/src",
        bug_tracking_url=bug_tracking_url,
        description=repo_data.get("description"),
        vcs_url=bb_url,
        primary_language=repo_data.get("language"),
        parties=[owner_party],
    )
    package.set_purl(purl)
    return package
