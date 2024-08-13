#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import hashlib
import logging
import re
from urllib.parse import urlparse

import requests
from packagedcode.maven import _parse
from packagedcode.maven import get_maven_pom
from packagedcode.maven import get_urls
from packagedcode.models import PackageData
from packageurl import PackageURL

from minecode import priority_router
from minecode.miners.maven import build_url_and_filename
from minecode.miners.maven import get_artifacts
from minecode.miners.maven import is_worthy_artifact
from minecode.utils import fetch_http
from minecode.utils import get_temp_file
from minecode.utils import validate_sha1
from packagedb.models import PackageContentType
from packagedb.models import PackageRelation
from packagedb.models import make_relationship

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRACE = False
TRACE_DEEP = False

if TRACE:
    import sys

    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


MAVEN_BASE_URL = "https://repo1.maven.org/maven2"
MAVEN_INDEX_URL = (
    "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"
)


class MavenNexusCollector:
    """
    Download and process a Nexus Maven index file.
    WARNING: Processing is rather long: a full index is ~600MB.
    """

    def fetch_index(self, uri=MAVEN_INDEX_URL, timeout=10):
        """
        Return a temporary location where the fetched content was saved.
        Does not return the content proper as a regular fetch does.

        `timeout` is a default timeout.
        """
        content = fetch_http(uri, timeout=timeout)
        temp_file = get_temp_file("NonPersistentHttpVisitor")
        with open(temp_file, "wb") as tmp:
            tmp.write(content)
        return temp_file

    def get_packages(self, content=None):
        """Yield Package objects from maven index"""
        if content:
            index_location = content
        else:
            index_location = self.fetch_index()

        artifacts = get_artifacts(index_location, worthyness=is_worthy_artifact)

        for artifact in artifacts:
            # we cannot do much without these
            group_id = artifact.group_id
            artifact_id = artifact.artifact_id
            version = artifact.version
            extension = artifact.extension

            if not (group_id and artifact_id and version and extension):
                continue

            qualifiers = {}
            if extension and extension != "jar":
                qualifiers["type"] = extension

            classifier = artifact.classifier
            if classifier:
                qualifiers["classifier"] = classifier

            # FIXME: also use the Artifact.src_exist flags too?

            # build a URL: This is the real JAR download URL
            # FIXME: this should be set at the time of creating Artifacts
            # instead togther with the filename... especially we could use
            # different REPOs.
            jar_download_url, _ = build_url_and_filename(
                group_id, artifact_id, version, extension, classifier
            )

            # FIXME: should this be set in the yielded URI too
            last_mod = artifact.last_modified

            urls = get_urls(
                namespace=group_id,
                name=artifact_id,
                version=version,
                qualifiers=qualifiers or None,
            )

            repository_homepage_url = urls["repository_homepage_url"]
            repository_download_url = urls["repository_download_url"]
            api_data_url = urls["api_data_url"]

            yield PackageData(
                type="maven",
                namespace=group_id,
                name=artifact_id,
                version=version,
                qualifiers=qualifiers or None,
                download_url=jar_download_url,
                size=artifact.size,
                sha1=artifact.sha1,
                release_date=last_mod,
                repository_homepage_url=repository_homepage_url,
                repository_download_url=repository_download_url,
                api_data_url=api_data_url,
            )


def get_pom_text(namespace, name, version, qualifiers={}, base_url=MAVEN_BASE_URL):
    """
    Return the contents of the POM file of the package described by the purl
    field arguments in a string.
    """
    # Create URLs using purl fields
    if qualifiers and not isinstance(qualifiers, dict):
        return
    urls = get_urls(
        namespace=namespace,
        name=name,
        version=version,
        qualifiers=qualifiers,
        base_url=base_url,
    )
    if not urls:
        return
    # Get and parse POM info
    pom_url = urls["api_data_url"]
    # TODO: manage different types of errors (404, etc.)
    response = requests.get(pom_url)
    if not response:
        return
    return response.text


def fetch_parent(pom_text, base_url=MAVEN_BASE_URL):
    """Return the parent pom text of `pom_text`, or None if `pom_text` has no parent."""
    if not pom_text:
        return
    pom = get_maven_pom(text=pom_text)
    if (
        pom.parent
        and pom.parent.group_id
        and pom.parent.artifact_id
        and pom.parent.version.version
    ):
        parent_namespace = pom.parent.group_id
        parent_name = pom.parent.artifact_id
        parent_version = str(pom.parent.version.version)
        parent_pom_text = get_pom_text(
            namespace=parent_namespace,
            name=parent_name,
            version=parent_version,
            qualifiers={},
            base_url=base_url,
        )
        return parent_pom_text


def get_ancestry(pom_text, base_url=MAVEN_BASE_URL):
    """
    Return a list of pom text of the ancestors of `pom`. The list is ordered
    from oldest ancestor to newest. The list is empty is there is no parent pom.
    """
    ancestors = []
    has_parent = True
    while has_parent:
        parent_pom_text = fetch_parent(pom_text=pom_text, base_url=base_url)
        if not parent_pom_text:
            has_parent = False
        else:
            ancestors.append(parent_pom_text)
            pom_text = parent_pom_text
    return reversed(ancestors)


def get_merged_ancestor_package_from_maven_package(package, base_url=MAVEN_BASE_URL):
    """
    Merge package details of a package with its ancestor pom
    and return the merged package.
    """
    if not package:
        return
    pom_text = get_pom_text(
        name=package.name,
        namespace=package.namespace,
        version=package.version,
        qualifiers=package.qualifiers,
        base_url=base_url,
    )
    merged_package = merge_ancestors(
        ancestor_pom_texts=get_ancestry(pom_text),
        package=package,
    )
    return merged_package


def merge_parent(package, parent_package):
    """Merge `parent_package` data into `package` and return `package."""
    mergeable_fields = (
        "declared_license_expression",
        "homepage_url",
        "parties",
    )
    for field in mergeable_fields:
        # If `field` is empty on the package we're looking at, populate
        # those fields with values from the parent package.
        if not getattr(package, field):
            value = getattr(parent_package, field)
            setattr(package, field, value)

            msg = f"Field `{field}` has been updated using values obtained from the parent POM {parent_package.purl}"
            history = package.extra_data.get("history")
            if history:
                package.extra_data["history"].append(msg)
            else:
                package.extra_data["history"] = [msg]

    return package


def merge_ancestors(ancestor_pom_texts, package):
    """
    Merge metadata from `ancestor_pom_text` into `package`.

    The order of POM content in `ancestor_pom_texts` is expected to be in the
    order of oldest ancestor to newest.
    """
    for ancestor_pom_text in ancestor_pom_texts:
        ancestor_package = _parse(
            datasource_id="maven_pom",
            package_type="maven",
            primary_language="Java",
            text=ancestor_pom_text,
        )
        package = merge_parent(package, ancestor_package)
    return package


def map_maven_package(
    package_url, package_content, pipelines, priority=0, reindex_metadata=False
):
    """
    Add a maven `package_url` to the PackageDB.

    Return an error string if errors have occured in the process.

    if ``reindex_metadata`` is True, only reindex metadata and DO NOT rescan the full package.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    db_package = None
    error = ""

    if "repository_url" in package_url.qualifiers:
        base_url = package_url.qualifiers["repository_url"]
    else:
        base_url = MAVEN_BASE_URL

    pom_text = get_pom_text(
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
        qualifiers=package_url.qualifiers,
        base_url=base_url,
    )
    if not pom_text:
        msg = f"Package does not exist on maven: {package_url}"
        error += msg + "\n"
        logger.error(msg)
        return db_package, error

    package = _parse(
        "maven_pom",
        "maven",
        "Java",
        text=pom_text,
        base_url=base_url,
    )
    ancestor_pom_texts = get_ancestry(pom_text=pom_text, base_url=base_url)
    package = merge_ancestors(ancestor_pom_texts=ancestor_pom_texts, package=package)

    urls = get_urls(
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
        qualifiers=package_url.qualifiers,
        base_url=base_url,
    )
    # In the case of looking up a maven package with qualifiers of
    # `classifiers=sources`, the purl of the package created from the pom does
    # not have the qualifiers, so we need to set them. Additionally, the download
    # url is not properly generated since it would be missing the sources bit
    # from the filename.
    package.qualifiers = package_url.qualifiers
    package.download_url = urls["repository_download_url"]
    package.repository_download_url = urls["repository_download_url"]

    # Set package_content value
    package.extra_data["package_content"] = package_content

    # If sha1 exists for a jar, we know we can create the package
    # Use pom info as base and create packages for binary and source package

    # Check to see if binary is available
    sha1 = get_package_sha1(package)
    if sha1:
        package.sha1 = sha1
        override = reindex_metadata
        db_package, _, _, _ = merge_or_create_package(
            package, visit_level=50, override=override
        )
    else:
        msg = f"Failed to retrieve JAR: {package_url}"
        error += msg + "\n"
        logger.error(msg)

    if not reindex_metadata:
        # Submit package for scanning
        if db_package:
            add_package_to_scan_queue(
                package=db_package, pipelines=pipelines, priority=priority
            )

    return db_package, error


def map_maven_binary_and_source(
    package_url, pipelines, priority=0, reindex_metadata=False
):
    """
    Get metadata for the binary and source release of the Maven package
    `package_url` and save it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ""
    package, emsg = map_maven_package(
        package_url=package_url,
        package_content=PackageContentType.BINARY,
        pipelines=pipelines,
        priority=priority,
        reindex_metadata=reindex_metadata,
    )
    if emsg:
        error += emsg

    source_package_url = package_url
    source_package_url.qualifiers["classifier"] = "sources"
    source_package, emsg = map_maven_package(
        package_url=source_package_url,
        package_content=PackageContentType.SOURCE_ARCHIVE,
        pipelines=pipelines,
        priority=priority,
        reindex_metadata=reindex_metadata,
    )
    if emsg:
        error += emsg

    if not reindex_metadata and package and source_package:
        make_relationship(
            from_package=source_package,
            to_package=package,
            relationship=PackageRelation.Relationship.SOURCE_PACKAGE,
        )

    return error


def map_maven_packages(package_url, pipelines):
    """
    Given a valid `package_url` with no version, get metadata for the binary and
    source release for each version of the Maven package `package_url` and save
    it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ""
    namespace = package_url.namespace
    name = package_url.name
    # Find all versions of this package
    query_params = f"g:{namespace}+AND+a:{name}"
    url = f"https://search.maven.org/solrsearch/select?q={query_params}&core=gav"
    response = requests.get(url)
    if response:
        package_listings = response.json().get("response", {}).get("docs", [])
    for listing in package_listings:
        purl = PackageURL(
            type="maven",
            namespace=listing.get("g"),
            name=listing.get("a"),
            version=listing.get("v"),
        )
        emsg = map_maven_binary_and_source(purl, pipelines)
        if emsg:
            error += emsg
    return error


def get_package_sha1(package):
    """
    Return the sha1 value for `package` by checking if the sha1 file exists for
    `package` on maven and returning the contents if it does.
    If the sha1 is invalid, we download the package's JAR and calculate the sha1
    from that.
    """
    download_url = package.repository_download_url
    sha1_download_url = f"{download_url}.sha1"
    response = requests.get(sha1_download_url)
    if response.ok:
        sha1_contents = response.text.strip().split()
        sha1 = sha1_contents[0]
        sha1 = validate_sha1(sha1)
        if not sha1:
            # Download JAR and calculate sha1 if we cannot get it from the repo
            response = requests.get(download_url)
            if response:
                sha1_hash = hashlib.new("sha1", response.content)
                sha1 = sha1_hash.hexdigest()
        return sha1


@priority_router.route("pkg:maven/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a maven Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from maven and
    using it to create a new PackageDB entry. The package is then added to the
    scan queue afterwards. We also get the Package information for the
    accompanying source package and add it to the PackageDB and scan queue, if
    available.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occured when parsing {purl_str}: {e}"
        return error

    has_version = bool(package_url.version)
    if has_version:
        reindex_metadata = kwargs.get("reindex_metadata", False)
        error = map_maven_binary_and_source(
            package_url,
            pipelines,
            reindex_metadata=reindex_metadata,
            priority=priority,
        )
    else:
        error = map_maven_packages(package_url, pipelines)

    return error


collect_links = re.compile(r'href="([^"]+)"').findall
collect_links_and_artifact_timestamps = re.compile(
    r'<a href="([^"]+)".*</a>\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|-)'
).findall


def check_if_file_name_is_linked_on_page(file_name, links, **kwargs):
    """Return True if `file_name` is in `links`"""
    return any(l.endswith(file_name) for l in links)


def check_if_page_has_pom_files(links, **kwargs):
    """Return True of any entry in `links` ends with .pom."""
    return any(l.endswith(".pom") for l in links)


def check_if_page_has_directories(links, **kwargs):
    """Return True if any entry, excluding "../", ends with /."""
    return any(l.endswith("/") for l in links if l != "../")


def check_if_package_version_page(links, **kwargs):
    """Return True if `links` contains pom files and has no directories"""
    return check_if_page_has_pom_files(
        links=links
    ) and not check_if_page_has_directories(links=links)


def check_if_package_page(links, **kwargs):
    return check_if_file_name_is_linked_on_page(
        file_name="maven-metadata.xml", links=links
    ) and not check_if_page_has_pom_files(links=links)


def check_if_maven_root(links, **kwargs):
    """
    Return True if "archetype-catalog.xml" is in `links`, as the root of a Maven
    repo contains "archetype-catalog.xml".
    """
    return check_if_file_name_is_linked_on_page(
        file_name="archetype-catalog.xml", links=links
    )


def check_on_page(url, checker):
    """
    Return True if there is a link on `url` that is the same as `file_name`,
    False otherwise.
    """
    response = requests.get(url)
    if response:
        links = collect_links(response.text)
        return checker(links=links)
    return False


def is_maven_root(url):
    """Return True if `url` is the root of a Maven repo, False otherwise."""
    return check_on_page(url, check_if_maven_root)


def is_package_page(url):
    """Return True if `url` is a package page on a Maven repo, False otherwise."""
    return check_on_page(url, check_if_package_page)


def is_package_version_page(url):
    """Return True if `url` is a package version page on a Maven repo, False otherwise."""
    return check_on_page(url, check_if_package_version_page)


def url_parts(url):
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    path_segments = [p for p in parsed_url.path.split("/") if p]
    return scheme, netloc, path_segments


def create_url(scheme, netloc, path_segments):
    url_template = f"{scheme}://{netloc}"
    path = "/".join(path_segments)
    return f"{url_template}/{path}"


def get_maven_root(url):
    """
    Given `url`, that is a URL to namespace, package, or artifact in a Maven
    repo, return the URL to the root of that repo. If a Maven root cannot be
    determined, return None.

    >>> get_maven_root('https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/')
    'https://repo1.maven.org/maven2'
    """
    scheme, netloc, path_segments = url_parts(url)
    for i in range(len(path_segments)):
        segments = path_segments[: i + 1]
        url_segment = create_url(scheme, netloc, segments)
        if is_maven_root(url_segment):
            return url_segment
    return None


def determine_namespace_name_version_from_url(url, root_url=None):
    """
    Return a 3-tuple containing strings of a Package namespace, name, and
    version, determined from `url`, where `url` points to namespace, package,
    specific package version, or artifact on a Maven repo.

    Return None if a Maven root cannot be determined from `url`.

    >>> determine_namespace_name_version_from_url('https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/')
    ('net.shibboleth', 'parent', '7.11.0')
    """
    if not root_url:
        root_url = get_maven_root(url)
        if not root_url:
            raise Exception(f"Error: not a Maven repository: {url}")

    _, remaining_path_segments = url.split(root_url)
    remaining_path_segments = remaining_path_segments.split("/")
    remaining_path_segments = [p for p in remaining_path_segments if p]

    namespace_segments = []
    package_name = ""
    package_version = ""
    for i in range(len(remaining_path_segments)):
        segment = remaining_path_segments[i]
        segments = remaining_path_segments[: i + 1]
        path = "/".join(segments)
        url_segment = f"{root_url}/{path}"
        if is_package_page(url_segment):
            package_name = segment
        elif is_package_version_page(url_segment):
            package_version = segment
        else:
            namespace_segments.append(segment)
    namespace = ".".join(namespace_segments)
    return namespace, package_name, package_version


def add_to_import_queue(url, root_url):
    """Create ImportableURI for the Maven repo package page at `url`."""
    from minecode.models import ImportableURI

    data = None
    response = requests.get(url)
    if response:
        data = response.text
    namespace, name, _ = determine_namespace_name_version_from_url(url, root_url)
    purl = PackageURL(
        type="maven",
        namespace=namespace,
        name=name,
    )
    importable_uri = ImportableURI.objects.insert(url, data, purl)
    if importable_uri:
        logger.info(f"Inserted {url} into ImportableURI queue")


def filter_only_directories(timestamps_by_links):
    """Given a mapping of `timestamps_by_links`, where the links are directory names (which end with `/`),"""
    timestamps_by_links_filtered = {}
    for link, timestamp in timestamps_by_links.items():
        if link != "../" and link.endswith("/"):
            timestamps_by_links_filtered[link] = timestamp
    return timestamps_by_links_filtered


valid_artifact_extensions = [
    "ejb3",
    "ear",
    "aar",
    "apk",
    "gem",
    "jar",
    "nar",
    # 'pom',
    "so",
    "swc",
    "tar",
    "tar.gz",
    "war",
    "xar",
    "zip",
]


def filter_for_artifacts(timestamps_by_links):
    """
    Given a mapping of `timestamps_by_links`, where the links are the filenames
    of Maven artifacts, return a mapping of filenames whose extension is in
    `valid_artifact_extensions` and their timestamps.
    """
    timestamps_by_links_filtered = {}
    for link, timestamp in timestamps_by_links.items():
        for ext in valid_artifact_extensions:
            if link.endswith(ext):
                timestamps_by_links_filtered[link] = timestamp
    return timestamps_by_links_filtered


def collect_links_from_text(text, filter):
    """
    Return a mapping of link locations and their timestamps, given HTML `text`
    content, that is filtered using `filter`.
    """
    links_and_timestamps = collect_links_and_artifact_timestamps(text)
    timestamps_by_links = {}
    for link, timestamp in links_and_timestamps:
        if timestamp == "-":
            timestamp = ""
        timestamps_by_links[link] = timestamp

    timestamps_by_links = filter(timestamps_by_links=timestamps_by_links)
    return timestamps_by_links


def create_absolute_urls_for_links(text, url, filter):
    """
    Given the `text` contents from `url`, return a mapping of absolute URLs to
    links from `url` and their timestamps, that is then filtered by `filter`.
    """
    timestamps_by_absolute_links = {}
    url = url.rstrip("/")
    timestamps_by_links = collect_links_from_text(text, filter)
    for link, timestamp in timestamps_by_links.items():
        if not link.startswith(url):
            link = f"{url}/{link}"
        timestamps_by_absolute_links[link] = timestamp
    return timestamps_by_absolute_links


def get_directory_links(url):
    """Return a list of absolute directory URLs of the hyperlinks from `url`"""
    timestamps_by_directory_links = {}
    response = requests.get(url)
    if response:
        timestamps_by_directory_links = create_absolute_urls_for_links(
            response.text, url=url, filter=filter_only_directories
        )
    return timestamps_by_directory_links


def get_artifact_links(url):
    """Return a list of absolute directory URLs of the hyperlinks from `url`"""
    timestamps_by_artifact_links = []
    response = requests.get(url)
    if response:
        timestamps_by_artifact_links = create_absolute_urls_for_links(
            response.text, url=url, filter=filter_for_artifacts
        )
    return timestamps_by_artifact_links


def crawl_to_package(url, root_url):
    """Given a maven repo `url`,"""
    if is_package_page(url):
        add_to_import_queue(url, root_url)
        return

    for link in get_directory_links(url):
        crawl_to_package(link, root_url)


def crawl_maven_repo_from_root(root_url):
    """
    Given the `url` to a maven root, traverse the repo depth-first and add
    packages to the import queue.
    """
    crawl_to_package(root_url, root_url)


def get_artifact_sha1(artifact_url):
    """Return the SHA1 value of the Maven artifact located at `artifact_url`."""
    sha1 = None
    artifact_sha1_url = f"{artifact_url}.sha1"
    response = requests.get(artifact_sha1_url)
    if response:
        sha1_contents = response.text.strip().split()
        sha1 = sha1_contents[0]
        sha1 = validate_sha1(sha1)
    return sha1


def get_classifier_from_artifact_url(
    artifact_url, package_version_page_url, package_name, package_version
):
    """
    Return the classifier from a Maven artifact URL `artifact_url`, otherwise
    return None if a classifier cannot be determined from `artifact_url`
    """
    classifier = None
    # https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0
    package_version_page_url = package_version_page_url.rstrip("/")
    # https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0
    leading_url_portion = f"{package_version_page_url}/{package_name}-{package_version}"
    # artifact_url = 'https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0-onejar.jar'
    # ['', '-onejar.jar']
    _, remaining_url_portion = artifact_url.split(leading_url_portion)
    # ['-onejar', 'jar']
    remaining_url_portions = remaining_url_portion.split(".")
    if remaining_url_portions and remaining_url_portions[0]:
        # '-onejar'
        classifier = remaining_url_portions[0]
        if classifier.startswith("-"):
            # 'onejar'
            classifier = classifier[1:]
    return classifier
