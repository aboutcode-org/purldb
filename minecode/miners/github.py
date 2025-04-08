#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging
from datetime import date
from datetime import datetime

import attr
import packagedcode.models as scan_models
from github.MainClass import Github
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import Mapper
from minecode.utils import form_vcs_url
from minecode.utils import parse_date

logger = logging.getLogger(__name__)

TRACE = False
if TRACE:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class GithubSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://api.github.com/repositories?since=0"


@visit_router.route(r"https://api.github.com/repositories\?since=\d+")
class GithubReposVisitor(HttpJsonVisitor):
    """
    Visitor to run repositories request to get all repositories by increasing since symbol 100 each loop time.
    Refer to: https://developer.github.com/v3/repos/#list-all-public-repositories
              https://api.github.com/repositories
    """

    def get_uris(self, content):
        repo_request_base = "https://api.github.com/repositories?since="
        has_content = False
        if content:
            for entry in content:
                has_content = True
                url = entry.get("url")
                # Take full_name instead of name here since we want to keep more info, especially when forming the package url
                #     "name": "grit",
                #     "full_name": "mojombo/grit",
                name = entry.get("full_name")
                if url:
                    package_url = None
                    if name:
                        package_url = PackageURL(type="github", name=name).to_string()
                    # Yield URI for GithubSingleRepoVisitor use
                    yield URI(uri=url, package_url=package_url, source_uri=self.uri)
        if not has_content:
            logger.info(
                f"The content of the response is empty, the processing might be finished for URI: {self.uri}"
            )
        else:
            uri = self.uri
            current_id = uri.replace("https://api.github.com/repositories?since=", "")
            current_id = int(current_id)
            # 100 is fixed since each page has 100 entries. Plus 100 means to go from next page.
            new_id = current_id + 100
            new_url = repo_request_base + str(new_id)
            yield URI(uri=new_url, source_uri=self.uri)


@visit_router.route(r"https://api.github.com/repos/[\w\-\.]+/[\w\-\.]+")
class GithubSingleRepoVisitor(HttpJsonVisitor):
    """
    Visitor to get the json and add more content with GitHub API from one repo.
    For example: https://api.github.com/repos/mojombo/grit
    """

    def fetch(self, uri, timeout=None):
        """
        Having its own fetch function instead of inheriting from HttpJsonVisitor class is because:
        The json itself has lots of URL info, the Github API can get content without acccessing the URLs inside the json explicitly.
        The main idea is to fetch download_url...
        """
        full_name = uri.replace("https://api.github.com/repos/", "")
        g = Github()
        repo = g.get_repo(full_name)

        common_data = dict(
            name=repo.name,
            description=repo.description,
            blobs_url=repo.blobs_url,
            language=repo.language,
            size=repo.size,
            homepage=repo.homepage,
            html_url=repo.html_url,
            etag=repo.etag,
            full_name=repo.full_name,
            repo_id=repo.id,
            ssh_url=repo.ssh_url,
            source_url=repo.svn_url,
            clone_url=repo.clone_url,
            watchers_count=repo.watchers,
            master_branch=repo.master_branch,
            updated_at=json_serial_date_obj(repo.updated_at),
            pushed_at=json_serial_date_obj(repo.pushed_at),
        )

        if repo.owner:
            common_data["owner"] = repo.owner.name
        if repo._issues_url:
            common_data["issue_url"] = repo._issues_url.value

        if repo._git_url:
            common_data["git_url"] = repo._git_url.value

        if repo.organization:
            repo.origanization = repo.organization.name

        downloads = []
        if repo.get_downloads():
            for download in list(repo.get_downloads()):
                downloads.append(
                    dict(
                        name=download.name,
                        url=download.url,
                        size=download.size,
                        s3_url=download.s3_url,
                        created_at=json_serial_date_obj(download.created_at),
                        download_count=download.download_count,
                        description=download.description,
                        redirect=download.redirect,
                        signature=download.signature,
                        html_url=download.html_url,
                        bucket=download.bucket,
                        acl=download.acl,
                        accesskeyid=download.accesskeyid,
                        expirationdate=json_serial_date_obj(download.expirationdate),
                    )
                )
        common_data["downloads"] = downloads

        tags = []
        if repo.get_tags():
            for tag in list(repo.get_tags()):
                tag_info = dict(
                    name=tag.name,
                    tarball_url=tag.tarball_url,
                    zipball_url=tag.zipball_url,
                )
                if tag.commit:
                    tag_info["sha1"] = tag.commit.sha
                tags.append(tag_info)
        common_data["tags"] = tags

        if not common_data.get("tags") and not common_data.get("downloads"):
            # If there is no downloads and tags, let's make the download_url by forming archive/master.zip at the end
            # For example, the base html is: https://github.com/collectiveidea/calendar_builder
            # The final download_url is https://github.com/collectiveidea/calendar_builder/archive/master.zip
            branches_download_urls = []
            download_url_bases = "{html_url}/archive/{branch_name}.zip"
            if repo.get_branches():
                for branch in list(repo.get_branches()):
                    branches_download_urls.append(
                        download_url_bases.format(
                            html_url=common_data.get("html_url"),
                            branch_name=branch.name,
                        )
                    )
            common_data["branches_download_urls"] = branches_download_urls

        common_data["labels"] = []
        if repo.get_labels():
            for label in repo.get_labels():
                common_data["labels"].append(label.name)

        return json.dumps(common_data)


def json_serial_date_obj(obj):
    """JSON serializer for date object"""
    if obj and isinstance(obj, datetime | date):
        return obj.isoformat()


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
        return build_github_packages(visited_data, resource_uri.uri, resource_uri.package_url)


def build_github_packages(visited_data, uri, purl=None):
    """
    Yield Package built from Github API visited_data as a JSON string.
    metadata: HTML metadata content
    uri: String value of the uri from ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    visited_data = json.loads(visited_data)

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
