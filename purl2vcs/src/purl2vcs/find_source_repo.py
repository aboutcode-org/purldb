#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import subprocess
from typing import Generator, List
from urllib.parse import urlparse

import requests
from packageurl import PackageURL
from packageurl.contrib.django.utils import purl_to_lookups
from packageurl.contrib.purl2url import get_download_url, purl2url
from scancode.api import get_urls as get_urls_from_location

from minecode.model_utils import add_package_to_scan_queue
from minecode.visitors.maven import get_merged_ancestor_package_from_maven_package
from packagedb.models import Package, PackageContentType, PackageSet

logger = logging.getLogger(__name__)


def get_urls_from_text(text):
    """
    Return the URLs found in a text
    """
    if not text:
        return
    lines = text.splitlines()
    # location can be a list of lines
    for url in get_urls_from_location(location=lines)["urls"]:
        yield url["url"]


# We keep track of unreachable URLs during a session
UNREACHABLE_URLS = set()

# We keep cache of the requests.Response of each URL during a session
RESPONSE_BY_URL_CACHE = {}


def fetch_response(
    url,
    timeout=10,
):
    """
    Return the request response for url or None, use a session cache
    and ignore unreachable URLs
    """
    try:
        if not url:
            return
        # This URL takes a lot of time to download
        # and it does not contain any data of use
        if not is_good_repo_url(url):
            return

        if not is_url_with_usable_content(url):
            return

        if url in UNREACHABLE_URLS:
            return

        response = RESPONSE_BY_URL_CACHE.get(url)
        if response:
            return response

        response = requests.get(url=url, timeout=timeout)
        if response.status_code != 200:
            UNREACHABLE_URLS.add(url)
            return

        RESPONSE_BY_URL_CACHE[url] = response
        return response

    except Exception as e:
        logger.error(f"Error getting {url}: {e}")
        UNREACHABLE_URLS.add(url)
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


def add_source_package_to_package_set(
    source_package,
    package,
):
    """
    Add ``source_package`` to the ``package`` package set. Create
    the package set if it doesn't exist
    """
    package_sets = package.package_sets.all()
    if not package_sets:
        # Create a Package set if we don't have one
        package_set = PackageSet.objects.create()
        package_set.add_to_package_set(package)
        package_sets = [package_set]

    for package_set in package_sets:
        package_set.add_to_package_set(source_package)
        logger.info(
            f"Assigned source repo package {source_package.purl} to Package set {package_set.uuid}"
        )


def get_source_package_and_add_to_package_set(package):
    """
    Process a package and add the source repository to the package set
    """
    source_purl = get_source_repo(package=package)

    if not source_purl:
        return

    try:
        download_url = get_download_url(str(source_purl))
        if not download_url:
            return
    except:
        logger.error(f"Error getting download_url for {source_purl}")
        return

    source_package = Package.objects.for_package_url(
        purl_str=str(source_purl)
    ).get_or_none()

    if not source_package:
        source_package, _created = Package.objects.get_or_create(
            type=source_purl.type,
            namespace=source_purl.namespace,
            name=source_purl.name,
            version=source_purl.version,
            download_url=download_url,
            package_content=PackageContentType.SOURCE_REPO,
        )
        add_package_to_scan_queue(source_package)
        logger.info(f"Created source repo package {source_purl} for {package.purl}")
    package_set_uuids = [item["uuid"] for item in package.package_sets.all().values("uuid")]
    package_set_ids = set(package_set_uuids)
    source_package_set_ids = set(source_package.package_sets.all().values_list("uuid"))

    # If the package exists and already in the set then there is nothing left to do
    if package_set_ids.intersection(source_package_set_ids):
        return

    add_source_package_to_package_set(
        source_package=source_package,
        package=package,
    )


def get_source_package_for_all_packages():
    """
    Add the PackageURL of the source repository of a Package
    if found
    """
    for package in Package.objects.all().paginated():
        get_source_package_and_add_to_package_set(package)


def get_source_repo(package: Package) -> PackageURL:
    """
    Return the PackageURL of the source repository of a Package
    or None if not found. Package is either a PackageCode Package object or
    Package instance object.
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
    Return a list of URLs of source repositories for a package,
    possibly empty.
    """
    if not package:
        return []
    metadata_urls = list(get_urls_from_package_data(package))
    if metadata_urls:
        return metadata_urls
    resource_urls = list(get_urls_from_package_resources(package))
    if resource_urls:
        return resource_urls
    return []


def convert_repo_urls_to_purls(source_urls):
    """
    Yield PURLs from a list from a list of source repository URLs.
    """
    for source_url in source_urls or []:
        yield from convert_repo_url_to_purls(source_url)


def convert_repo_url_to_purls(source_url):
    """
    Yield PURLs from a single source repository URL.
    """
    url_hints = [
        "github",
        "gitlab",
        "bitbucket",
    ]
    # URL like: git@github.com+https://github.com/graphql-java/java-dataloader.git
    if source_url.startswith("git@github.com+"):
        _, _, source_url = source_url.partition("+")

    # VCS URL like: https+//github.com/graphql-java-kickstart/graphql-java-servlet.git
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

    # git:: URLs
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
        return

    namespace = path_segments[1]
    name = path_segments[2]
    if not name:
        return

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
    found_urls = [
        package.code_view_url,
        package.homepage_url,
        package.bug_tracking_url,
        package.repository_homepage_url,
        package.vcs_url,
        package.repository_download_url,
    ]

    homepage_response = fetch_response(url=package.homepage_url)
    homepage_text = homepage_response and homepage_response.text
    found_urls.extend(get_urls_from_text(text=homepage_text))

    repository_homepage_response = fetch_response(url=package.repository_homepage_url)
    repository_homepage_text = (
        repository_homepage_response and repository_homepage_response.text
    )
    found_urls.extend(get_urls_from_text(text=repository_homepage_text))

    found_urls.extend(get_urls_from_text(text=package.description))

    yield from get_git_repo_urls(urls=found_urls)


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
                resp = fetch_response(url=url)
                url = resp and resp.url
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
        resp = fetch_response(url=repo_url)
        url = resp and resp.url
        if not url:
            return
        if not is_good_repo_url(repo_url):
            return
        output = subprocess.getoutput(f"git ls-remote {repo_url}")
        yield from get_tags_and_commits_from_git_output(output)
    except Exception as e:
        logger.error(f"Error getting tags and commits for {source_purl}: {e}")


def is_good_repo_url(url):
    """
    Return True if it's a good repo URL or
    False if it's some kind of problematic URL that we want to skip
    """
    # This is a jQuery Plugins Site Reserved Word and we don't want to scan it
    if url.startswith("https://github.com/assets"):
        return False
    return True


def is_url_with_usable_content(url):
    """
    Return True if this URL contains usable
    text data, otherwise False. Usable here means it is text
    and we are likely to find interesting URLs in that.
    """
    not_supported_extensions = (
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
    )
    if url.endswith(not_supported_extensions):
        return False
    return True


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


def get_package_object_from_purl(package_url):
    """
    Get a ``Package`` object for a ``package_url`` string.
    """
    lookups = purl_to_lookups(package_url)
    packages = Package.objects.filter(**lookups)
    packages_count = packages.count()

    if packages_count == 1:
        package = packages.first()
        return package

    if not packages_count:
        return

    if packages_count > 1:
        # Get the binary package
        # We use .get(qualifiers="") because the binary maven JAR has no qualifiers
        package = packages.get_or_none(qualifiers="")
        if not package:
            print(f"\t{package_url} does not exist in this database. Continuing.")
            return
