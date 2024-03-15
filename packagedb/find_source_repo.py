#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import enum
import logging
import subprocess
from typing import Generator
from typing import List
from urllib.parse import urlparse

import requests
from packageurl import PackageURL
from packageurl.contrib.purl2url import get_download_url
from packageurl.contrib.purl2url import purl2url
from scancode.api import get_urls as get_urls_from_location

from minecode.model_utils import add_package_to_scan_queue
from minecode.collectors.maven import get_merged_ancestor_package_from_maven_package
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet

logger = logging.getLogger(__name__)


class URLDataReturnType(enum.Enum):
    """
    Return type for get_urls_from_text
    """

    url = "url" # This the final URL after redirects
    text = "text" # This is the text of the response


non_reachable_urls = [
]
CACHE = {
    #    url: data
}


def get_urls_from_text(text):
    """
    Return the URLs found in a text
    """
    lines = text.splitlines()
    # location can be a list of lines
    for url in get_urls_from_location(location=lines)["urls"]:
        yield url["url"]


def get_data_from_response(response, data_type=URLDataReturnType.text):
    """
    Return the data from a response
    """
    if not response:
        return
    data_by_type = {
        URLDataReturnType.url: response.url,
        URLDataReturnType.text: response.text,
    }
    if data_type in data_by_type:
        return data_by_type[data_type]
    else:
        raise ValueError(f"Invalid data_type: {data_type}")


def get_data_from_url(
    url,
    data_type=URLDataReturnType.text,
    timeout=10,
):
    """
    Take a ``url`` as input and return the data from the URL
    depending on the ``data_type`` return URL or text if ``data_type`` is
    ``URLDataReturnType.url`` or ``URLDataReturnType.text`` respectively.
    """
    try:
        if not url:
            return
        if url.startswith("https://github.com/assets"):
            return
        not_supported_extensions = [
            ".pdf",
            ".zip",
            ".woff2",
            ".jar",
            ".js",
            ".png",
            ".css",
            ".svg",
            ".jpg",
            ".tgz",
        ]
        for extension in not_supported_extensions:
            if url.endswith(extension):
                return
        if url in non_reachable_urls:
            return
        if url in CACHE:
            response = CACHE[url]
            return get_data_from_response(response=response, data_type=data_type)
        response = requests.get(url=url, timeout=timeout)
        if response.status_code != 200:
            non_reachable_urls.append(url)
            return
        CACHE[url] = response
        return get_data_from_response(response=response, data_type=data_type)
    except Exception as e:
        logger.error(f"Error getting {url}: {e}")
        non_reachable_urls.append(url)
        return


def convert_apache_svn_to_github_url(url):
    """
    Convert an SVN URL to a GitHub URL
    >>> convert_apache_svn_to_github_url("svn+https://svn.apache.org/repos/asf/cdi/tags/1.0/cdi-extension-el-jsp")
    'https://github.com/apache/cdi/tree/1.0'
    """
    # svn+https://svn.apache.org/repos/asf/{name}/tags/{tag}/cdi-extension-el-jsp
    if "svn+" in url:
        _, _, url = url.partition("svn+")
    urlparsed_result = urlparse(url=url)
    # https://github.com/apache/{name}/tree/{tag}
    if urlparsed_result.netloc != "svn.apache.org":
        return
    path = urlparsed_result.path
    path_segs = path.split("/")
    if len(path_segs) < 6:
        return
    if path_segs[1] != "repos":
        return
    if path_segs[2] != "asf":
        return
    if path_segs[4] != "tags":
        return
    name = path_segs[3]
    tag = path_segs[5]
    return f"https://github.com/apache/{name}/tree/{tag}"


def add_source_repo_to_package_set(
    source_repo_type,
    source_repo_name,
    source_repo_namespace,
    source_repo_version,
    download_url,
    purl,
    source_purl,
    package,
):
    """
    Take source repo package information, create source package
    and add it to a Package set
    """
    # Create new Package from the source_purl fields
    source_repo_package, created = Package.objects.get_or_create(
        type=source_repo_type,
        namespace=source_repo_namespace,
        name=source_repo_name,
        version=source_repo_version,
        download_url=download_url,
        package_content=PackageContentType.SOURCE_REPO,
    )
    package_sets = package.package_sets.all()
    if not package_sets:
        # Create a Package set if we don't have one
        package_set = PackageSet.objects.create()
        package_set.add_to_package_set(package)
        package_set.add_to_package_set(source_repo_package)
    else:
        for package_set in package_sets.all():
            package_set.add_to_package_set(source_repo_package)
    if created:
        add_package_to_scan_queue(source_repo_package)
        logger.info(f"\tCreated source repo package {source_purl} for {purl}")
    else:
        logger.info(
            f"\tAssigned source repo package {source_purl} to Package set {package_set.uuid}"
        )


def get_source_repo_and_add_to_package_set():
    """
    Add the PackageURL of the source repository of a Package
    if found
    """
    for package in Package.objects.all().paginated():
        source_purl_with_tag = get_source_repo(package=package)
        download_url = None
        try:
            download_url = get_download_url(str(source_purl_with_tag))
        except:
            logger.error(f"Error getting download_url for {source_purl_with_tag}")
            continue
        if not download_url:
            continue
        add_source_repo_to_package_set(
            source_repo_type=source_purl_with_tag.type,
            source_repo_name=source_purl_with_tag.name,
            source_repo_namespace=source_purl_with_tag.namespace,
            source_repo_version=source_purl_with_tag.version,
            download_url=download_url,
            purl=package.purl,
            source_purl=source_purl_with_tag,
            package=package,
        )


def get_source_repo(package: Package) -> PackageURL:
    """
    Return the PackageURL of the source repository of a Package
    or None if not found
    """
    repo_urls = list(get_repo_urls(package))
    if not repo_urls:
        return
    # dedupe repo urls
    repo_urls = list(set(repo_urls))
    source_purls = list(convert_repo_urls_to_purls(repo_urls))
    if not source_purls:
        return
    source_purls = list(set(source_purls))
    source_purl_with_tag = find_package_version_tag_and_commit(
        version=package.version, source_purls=source_purls
    )
    if source_purl_with_tag:
        return source_purl_with_tag


def get_repo_urls(package: Package) -> Generator[str, None, None]:
    """
    Return the URL of the source repository of a package
    """
    source_urls = get_source_urls_from_package_data_and_resources(package=package)
    if source_urls:
        yield from source_urls

    # TODO: Use univers to sort versions
    # TODO: Also consider using dates https://github.com/nexB/purldb/issues/136
    for version_package in package.get_all_versions().order_by("-version"):
        source_urls = get_source_urls_from_package_data_and_resources(
            package=version_package
        )
        if source_urls:
            yield from source_urls

    if package.type == "maven":
        yield from get_source_urls_from_package_data_and_resources(
            package=get_merged_ancestor_package_from_maven_package(package=package)
        )


def get_source_urls_from_package_data_and_resources(package: Package) -> List[str]:
    """
    Return the URL of the source repository of a package
    or None if not found
    """
    if not package:
        return []
    source_urls = list(get_urls_from_package_data(package))
    if source_urls:
        return source_urls
    source_urls = list(get_urls_from_package_resources(package))
    if source_urls:
        return source_urls
    return []


def convert_repo_urls_to_purls(source_urls):
    """
    Convert a source URL to a purl
    """
    url_hints = [
        "github",
        "gitlab",
        "bitbucket",
    ]
    if not source_urls:
        return
    for source_url in source_urls:
        # git@github.com+https://github.com/graphql-java/java-dataloader.git
        if source_url.startswith("git@github.com+"):
            _, _, source_url = source_url.partition("+")
        # https+//github.com/graphql-java-kickstart/graphql-java-servlet.git
        if source_url.startswith("https+//"):
            # convert https+// to https://
            source_url = source_url.replace("https+//", "https://")
        if (
            source_url.startswith("git+https://") or source_url.startswith("git://")
        ) and "@" in source_url:
            # remove the commit from the end of the URL
            source_url, _, _ = source_url.rpartition("@")
        # remove .git from the end of the URL
        if source_url.endswith(".git"):
            source_url, _, _ = source_url.rpartition(".git")
        if source_url.startswith("git://"):
            # remove git:// from the beginning of the URL
            _, _, source_url = source_url.partition("git://")
            if ":" in source_url:
                # convert : to /
                source_url = source_url.replace(":", "/")
            source_url = f"https://{source_url}"
        urlparse_result = urlparse(source_url)
        path_segments = urlparse_result.path.split("/")
        if not len(path_segments) > 2:
            continue
        namespace = path_segments[1]
        name = path_segments[2]
        if not name:
            continue
        for url_hint in url_hints:
            if url_hint in urlparse_result.netloc:
                yield PackageURL(
                    type=url_hint,
                    namespace=namespace,
                    name=name,
                )


def get_urls_from_package_resources(package):
    """
    Return the URL of the source repository of a package
    """
    for resource in package.resources.filter(is_key_file=True):
        urls = [url["url"] for url in resource.urls]
        yield from get_git_repo_urls(urls=urls)


def get_urls_from_package_data(package) -> Generator[str, None, None]:
    """
    Return the URL of the source repository of a package
    """
    # TODO: Use the source package url
    # TODO: If the package is already a repo package then don't do anything
    # TODO: Search for URLs in description, qualifiers, download_url, notice_text, extracted_license_statement.
    description = package.description or ""
    urls_from_description_and_homepage_urls = (
        get_urls_from_description_and_homepage_urls(package, description)
    )
    urls = [
        package.code_view_url,
        package.homepage_url,
        package.bug_tracking_url,
        package.repository_homepage_url,
        package.vcs_url,
        package.repository_download_url,
    ]
    urls.extend(urls_from_description_and_homepage_urls)
    yield from get_git_repo_urls(urls=urls)


def get_urls_from_description_and_homepage_urls(package, description):
    homepage_text = get_data_from_url(
        url=package.homepage_url, data_type=URLDataReturnType.text
    )
    repository_homepage_text = get_data_from_url(
        url=package.repository_homepage_url, data_type=URLDataReturnType.text
    )
    if homepage_text:
        description += homepage_text
    if repository_homepage_text:
        description += repository_homepage_text
    urls_from_description = list(get_urls_from_text(text=description))
    return urls_from_description


def get_git_repo_urls(urls):
    """
    Return the first URL that contains a git repo URL
    """
    # TODO: Refine this
    url_hints = [
        "github",
        "gitlab",
        "bitbucket",
    ]
    for url in urls:
        if not url:
            continue
        if "svn.apache.org" in url:
            url = convert_apache_svn_to_github_url(url)
        if url and any(url_hint in url for url_hint in url_hints):
            yield url
        else:
            if url and url.startswith("git+"):
                _, _, url = url.partition("git+")
            try:
                url = get_data_from_url(
                    url=url, data_type=URLDataReturnType.url
                )
                if not url:
                    continue
            except Exception as e:
                logger.error(f"Error getting {url}: {e}")
                continue
            if any(url_hint in url for url_hint in url_hints):
                yield url


def get_tags_and_commits(source_purl):
    """
    Yield tuples of (tag, commit), given a source_purl PackageURL
    """
    try:
        repo_url = purl2url(str(source_purl))
        if not get_data_from_url(url=repo_url, data_type=URLDataReturnType.url):
            return
        # This is a jQuery Plugins Site Reserved Word and we don't want to scan it
        if repo_url.startswith("https://github.com/assets"):
            return
        output = subprocess.getoutput(f"git ls-remote {repo_url}")
        yield from get_tags_and_commits_from_git_output(output)
    except Exception as e:
        logger.error(f"Error getting tags and commits for {source_purl}: {e}")


def get_tags_and_commits_from_git_output(git_ls_remote):
    """
    Yield tuples of (tag, commit), given a git ls-remote output
    """
    for line in git_ls_remote.split("\n"):
        # line: kjwfgeklngelkfjofjeo123   refs/tags/1.2.3
        line_segments = line.split("\t")
        # segments: ["kjwfgeklngelkfjofjeo123", "refs/tags/1.2.3"]
        if len(line_segments) > 1 and line_segments[1].startswith("refs/tags/"):
            commit = line_segments[0]
            tag = line_segments[1].replace("refs/tags/", "")
            yield tag, commit


def get_tag_and_commit(version, tags_and_commits):
    """
    Return a tuple of (tag, commit) given a package version string or
    None if no matching tag and commit is found
    """
    version = version.lower()
    for tag, commit in tags_and_commits:
        modified_tag = tag.lower()
        # if tag looks like 1_2_3 convert it to 1.2.3
        modified_tag = modified_tag.replace("_", ".")
        # strip the leading v
        modified_tag = modified_tag.lstrip("v")
        # TODO: Handle other conventions to better match a version and a tag
        if modified_tag == version:
            return tag, commit


def find_package_version_tag_and_commit(version, source_purls):
    """
    Return a tuple of (tag, commit) given a package version string and source_purl PackageURL
    return None if no matching tag and commit is found
    """
    for source_purl in source_purls:
        tags_and_commits = get_tags_and_commits(source_purl=source_purl)
        tag_and_commit = get_tag_and_commit(
            version=version, tags_and_commits=tags_and_commits
        )
        if not tag_and_commit:
            continue
        tag, commit = tag_and_commit
        return PackageURL(
            type=source_purl.type,
            namespace=source_purl.namespace,
            name=source_purl.name,
            version=tag,
            qualifiers={"commit": commit},
        )
