#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import namedtuple
import gzip
import hashlib
import io
import json
import logging
import re
from typing import Dict
from urllib.parse import urlparse

import arrow
import requests
from bs4 import BeautifulSoup
from dateutil import tz

from jawa.util.utf import decode_modified_utf8
import javaproperties

from packageurl import PackageURL
from packagedcode.maven import build_filename
from packagedcode.maven import build_url
from packagedcode.maven import get_urls
from packagedcode.maven import _parse
from packagedcode.maven import get_maven_pom
from packageurl import PackageURL

from minecode import seed
from minecode import priority_router
from minecode import visit_router
from minecode.visitors import java_stream
from minecode.visitors import HttpVisitor
from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import URI
from minecode.utils import validate_sha1
from packagedb.models import make_relationship
from packagedb.models import PackageContentType
from packagedb.models import PackageRelation

"""
This module handles the Maven repositories such as central and other
nexus-based maven repositories. This is dubbed the maven2 format for the
repository and support the v4 POM format.

Old Maven1 format repositories are not supported (e.g. with jars,
sources, poms directories and POM format v2/v3).
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRACE = False
TRACE_DEEP = False

if TRACE:
    logger.setLevel(logging.DEBUG)


MAVEN_BASE_URL = 'https://repo1.maven.org/maven2'


class GzipFileWithTrailing(gzip.GzipFile):
    """
    A subclass of gzip.GzipFile supporting files with trailing garbage. Ignore
    the garbage.
    """
    # TODO: what is first_file??
    first_file = True
    gzip_magic = b'\037\213'
    has_trailing_garbage = False

    def _read_gzip_header(self):
        # read the first two bytes
        magic = self.fileobj.read(2)
        # rewind two bytes back
        self.fileobj.seek(-2, os.SEEK_CUR)
        is_gzip = magic != self.gzip_magic
        if is_gzip and not self.first_file:
            self.first_file = False
            self.has_trailing_garbage = True
            raise EOFError('Trailing garbage found')

        self.first_file = False
        gzip.GzipFile._read_gzip_header(self)


class MavenSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz'
        yield 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties'
        # yield 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.457.gz'
        # yield 'http://jcenter.bintray.com/'
        # yield 'https://repo2.maven.org/maven2/.index/nexus-maven-repository-index.gz'
        # other repos: http://stackoverflow.com/a/161846/302521
        # 1. google has a mirror https://www.infoq.com/news/2015/11/maven-central-at-google
        #     https://maven-central.storage.googleapis.com/repos/central/data/.index/nexus-maven-repository-index.properties
        # 2. apache has a possible mirro at http://repo.maven.apache.org/maven2/.index/nexus-maven-repository-index.properties
        # 3. ibiblio has an out of date mirror that has no directory listing and was last updated on 20161121171437
        # clojars is not a mirror, but its own repo: https://clojars.org/repo/.index/
        # other mirrors https://www.google.com/search?q=allinurl%3A%20.index%2Fnexus-maven-repository-index.properties&pws=0&gl=us&gws_rd=cr
        # also has a npm mirrors: https://maven-eu.nuxeo.org/nexus/#view-repositories;npmjs~browsestorage


def get_pom_text(namespace, name, version, qualifiers={}, base_url=MAVEN_BASE_URL):
    """
    Return the contents of the POM file of the package described by the purl
    field arguments in a string.
    """
    # Create URLs using purl fields
    if qualifiers and not isinstance(qualifiers, Dict):
        return
    urls = get_urls(
        namespace=namespace,
        name=name,
        version=version,
        qualifiers=qualifiers,
        base_url=base_url,
    )
    # Get and parse POM info
    pom_url = urls['api_data_url']
    # TODO: manage different types of errors (404, etc.)
    response = requests.get(pom_url)
    if not response:
        return
    return response.text


def fetch_parent(pom_text, base_url=MAVEN_BASE_URL):
    """
    Return the parent pom text of `pom_text`, or None if `pom_text` has no parent.
    """
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
    """
    Merge `parent_package` data into `package` and return `package.
    """
    mergeable_fields = (
        'declared_license_expression',
        'homepage_url',
        'parties',
    )
    for field in mergeable_fields:
        # If `field` is empty on the package we're looking at, populate
        # those fields with values from the parent package.
        if not getattr(package, field):
            value = getattr(parent_package, field)
            setattr(package, field, value)

            msg = f'Field `{field}` has been updated using values obtained from the parent POM {parent_package.purl}'
            history = package.extra_data.get('history')
            if history:
                package.extra_data['history'].append(msg)
            else:
                package.extra_data['history'] = [msg]

    return package


def merge_ancestors(ancestor_pom_texts, package):
    """
    Merge metadata from `ancestor_pom_text` into `package`.

    The order of POM content in `ancestor_pom_texts` is expected to be in the
    order of oldest ancestor to newest.
    """
    for ancestor_pom_text in ancestor_pom_texts:
        ancestor_package = _parse(
            datasource_id='maven_pom',
            package_type='maven',
            primary_language='Java',
            text=ancestor_pom_text
        )
        package = merge_parent(package, ancestor_package)
    return package


def map_maven_package(package_url, package_content):
    """
    Add a maven `package_url` to the PackageDB.

    Return an error string if errors have occured in the process.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    db_package = None
    error = ''

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
        msg = f'Package does not exist on maven: {package_url}'
        error += msg + '\n'
        logger.error(msg)
        return db_package, error

    package = _parse(
        'maven_pom',
        'maven',
        'Java',
        text=pom_text,
        base_url=base_url,
    )
    ancestor_pom_texts = get_ancestry(pom_text=pom_text, base_url=base_url)
    package = merge_ancestors(
        ancestor_pom_texts=ancestor_pom_texts,
        package=package
    )


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
    package.download_url = urls['repository_download_url']
    package.repository_download_url = urls['repository_download_url']

    # Set package_content value
    package.extra_data['package_content'] = package_content

    # If sha1 exists for a jar, we know we can create the package
    # Use pom info as base and create packages for binary and source package

    # Check to see if binary is available
    sha1 = get_package_sha1(package)
    if sha1:
        package.sha1 = sha1
        db_package, _, _, _ = merge_or_create_package(package, visit_level=50)
    else:
        msg = f'Failed to retrieve JAR: {package_url}'
        error += msg + '\n'
        logger.error(msg)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package)

    return db_package, error


def map_maven_binary_and_source(package_url):
    """
    Get metadata for the binary and source release of the Maven package
    `package_url` and save it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ''
    package, emsg = map_maven_package(
        package_url,
        PackageContentType.BINARY
    )
    if emsg:
        error += emsg

    source_package_url = package_url
    source_package_url.qualifiers['classifier'] = 'sources'
    source_package, emsg = map_maven_package(
        source_package_url,
        PackageContentType.SOURCE_ARCHIVE
    )
    if emsg:
        error += emsg

    if package and source_package:
        make_relationship(
            from_package=source_package,
            to_package=package,
            relationship=PackageRelation.Relationship.SOURCE_PACKAGE
        )

    return error


def map_maven_packages(package_url):
    """
    Given a valid `package_url` with no version, get metadata for the binary and
    source release for each version of the Maven package `package_url` and save
    it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ''
    namespace = package_url.namespace
    name = package_url.name
    # Find all versions of this package
    query_params = f'g:{namespace}+AND+a:{name}'
    url = f'https://search.maven.org/solrsearch/select?q={query_params}&core=gav'
    response = requests.get(url)
    if response:
        package_listings = response.json().get('response', {}).get('docs', [])
    for listing in package_listings:
        purl = PackageURL(
            type='maven',
            namespace=listing.get('g'),
            name=listing.get('a'),
            version=listing.get('v')
        )
        emsg = map_maven_binary_and_source(purl)
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
    sha1_download_url = f'{download_url}.sha1'
    response = requests.get(sha1_download_url)
    if response.ok:
        sha1_contents = response.text.strip().split()
        sha1 = sha1_contents[0]
        sha1 = validate_sha1(sha1)
        if not sha1:
            # Download JAR and calculate sha1 if we cannot get it from the repo
            response = requests.get(download_url)
            if response:
                sha1_hash = hashlib.new('sha1', response.content)
                sha1 = sha1_hash.hexdigest()
        return sha1


@priority_router.route('pkg:maven/.*')
def process_request(purl_str):
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
    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f'error occured when parsing {purl_str}: {e}'
        return error

    has_version = bool(package_url.version)
    if has_version:
        error = map_maven_binary_and_source(package_url)
    else:
        error = map_maven_packages(package_url)

    return error


collect_links = re.compile(r'href="([^"]+)"').findall
collect_links_and_artifact_timestamps = re.compile(
    r'<a href="([^"]+)".*</a>\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|-)'
).findall


def check_if_file_name_is_linked_on_page(file_name, links, **kwargs):
    """
    Return True if `file_name` is in `links`
    """
    return any(l.endswith(file_name) for l in links)


def check_if_page_has_pom_files(links, **kwargs):
    """
    Return True of any entry in `links` ends with .pom.
    """
    return any(l.endswith('.pom') for l in links)


def check_if_page_has_directories(links, **kwargs):
    """
    Return True if any entry, excluding "../", ends with /.
    """
    return any(l.endswith('/') for l in links if l != '../')


def check_if_package_version_page(links, **kwargs):
    """
    Return True if `links` contains pom files and has no directories
    """
    return (
        check_if_page_has_pom_files(links=links)
        and not check_if_page_has_directories(links=links)
    )


def check_if_package_page(links, **kwargs):
    return (
        check_if_file_name_is_linked_on_page(file_name='maven-metadata.xml', links=links)
        and not check_if_page_has_pom_files(links=links)
    )


def check_if_maven_root(links, **kwargs):
    """
    Return True if "archetype-catalog.xml" is in `links`, as the root of a Maven
    repo contains "archetype-catalog.xml".
    """
    return check_if_file_name_is_linked_on_page(file_name='archetype-catalog.xml', links=links)


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
    """
    Return True if `url` is the root of a Maven repo, False otherwise.
    """
    return check_on_page(url, check_if_maven_root)


def is_package_page(url):
    """
    Return True if `url` is a package page on a Maven repo, False otherwise.
    """
    return check_on_page(url, check_if_package_page)


def is_package_version_page(url):
    """
    Return True if `url` is a package version page on a Maven repo, False otherwise.
    """
    return check_on_page(url, check_if_package_version_page)


def url_parts(url):
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    path_segments = [p for p in parsed_url.path.split('/') if p]
    return scheme, netloc, path_segments


def create_url(scheme, netloc, path_segments):
    url_template = f'{scheme}://{netloc}'
    path = '/'.join(path_segments)
    return f'{url_template}/{path}'


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
        segments = path_segments[:i+1]
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
            raise Exception(f'Error: not a Maven repository: {url}')

    _, remaining_path_segments = url.split(root_url)
    remaining_path_segments = remaining_path_segments.split('/')
    remaining_path_segments = [p for p in remaining_path_segments if p]

    namespace_segments = []
    package_name = ''
    package_version = ''
    for i in range(len(remaining_path_segments)):
        segment = remaining_path_segments[i]
        segments = remaining_path_segments[:i+1]
        path = '/'.join(segments)
        url_segment = f'{root_url}/{path}'
        if is_package_page(url_segment):
            package_name = segment
        elif is_package_version_page(url_segment):
            package_version = segment
        else:
            namespace_segments.append(segment)
    namespace = '.'.join(namespace_segments)
    return namespace, package_name, package_version


def add_to_import_queue(url, root_url):
    """
    Create ImportableURI for the Maven repo package page at `url`.
    """
    from minecode.models import ImportableURI
    data = None
    response = requests.get(url)
    if response:
        data = response.text
    namespace, name, _ = determine_namespace_name_version_from_url(url, root_url)
    purl = PackageURL(
        type='maven',
        namespace=namespace,
        name=name,
    )
    importable_uri = ImportableURI.objects.insert(url, data, purl)
    if importable_uri:
        logger.info(f'Inserted {url} into ImportableURI queue')


def filter_only_directories(timestamps_by_links):
    """
    Given a mapping of `timestamps_by_links`, where the links are directory names (which end with `/`),
    """
    timestamps_by_links_filtered = {}
    for link, timestamp in timestamps_by_links.items():
        if link != '../' and link.endswith('/'):
            timestamps_by_links_filtered[link] = timestamp
    return timestamps_by_links_filtered


valid_artifact_extensions = [
    'ejb3',
    'ear',
    'aar',
    'apk',
    'gem',
    'jar',
    'nar',
    # 'pom',
    'so',
    'swc',
    'tar',
    'tar.gz',
    'war',
    'xar',
    'zip',
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
        if timestamp == '-':
            timestamp = ''
        timestamps_by_links[link] = timestamp

    timestamps_by_links = filter(timestamps_by_links=timestamps_by_links)
    return timestamps_by_links


def create_absolute_urls_for_links(text, url, filter):
    """
    Given the `text` contents from `url`, return a mapping of absolute URLs to
    links from `url` and their timestamps, that is then filtered by `filter`.
    """
    timestamps_by_absolute_links = {}
    url = url.rstrip('/')
    timestamps_by_links = collect_links_from_text(text, filter)
    for link, timestamp in timestamps_by_links.items():
        if not link.startswith(url):
            link = f'{url}/{link}'
        timestamps_by_absolute_links[link] = timestamp
    return timestamps_by_absolute_links


def get_directory_links(url):
    """
    Return a list of absolute directory URLs of the hyperlinks from `url`
    """
    timestamps_by_directory_links = {}
    response = requests.get(url)
    if response:
        timestamps_by_directory_links = create_absolute_urls_for_links(
            response.text,
            url=url,
            filter=filter_only_directories
        )
    return timestamps_by_directory_links


def get_artifact_links(url):
    """
    Return a list of absolute directory URLs of the hyperlinks from `url`
    """
    timestamps_by_artifact_links = []
    response = requests.get(url)
    if response:
        timestamps_by_artifact_links = create_absolute_urls_for_links(
            response.text,
            url=url,
            filter=filter_for_artifacts
        )
    return timestamps_by_artifact_links


def crawl_to_package(url, root_url):
    """
    Given a maven repo `url`,
    """
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
    """
    Return the SHA1 value of the Maven artifact located at `artifact_url`.
    """
    sha1 = None
    artifact_sha1_url = f'{artifact_url}.sha1'
    response = requests.get(artifact_sha1_url)
    if response:
        sha1_contents = response.text.strip().split()
        sha1 = sha1_contents[0]
        sha1 = validate_sha1(sha1)
    return sha1


def get_classifier_from_artifact_url(artifact_url, package_version_page_url, package_name, package_version):
    """
    Return the classifier from a Maven artifact URL `artifact_url`, otherwise
    return None if a classifier cannot be determined from `artifact_url`
    """
    classifier = None
    # https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0
    package_version_page_url = package_version_page_url.rstrip('/')
    # https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0
    leading_url_portion = f'{package_version_page_url}/{package_name}-{package_version}'
    # artifact_url = 'https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0-onejar.jar'
    # ['', '-onejar.jar']
    _, remaining_url_portion = artifact_url.split(leading_url_portion)
    # ['-onejar', 'jar']
    remaining_url_portions = remaining_url_portion.split('.')
    if remaining_url_portions and remaining_url_portions[0]:
        # '-onejar'
        classifier = remaining_url_portions[0]
        if classifier.startswith('-'):
            # 'onejar'
            classifier = classifier[1:]
    return classifier


@visit_router.route('http://repo1\.maven\.org/maven2/\.index/nexus-maven-repository-index.properties')
@visit_router.route('https://repo1\.maven\.org/maven2/\.index/nexus-maven-repository-index.properties')
class MavenNexusPropertiesVisitor(NonPersistentHttpVisitor):
    """
    Fetch the property files, parse the create the URI for each increment index
    """

    def get_uris(self, content):
        """
        Parse a NEXUS index properties file and yield increment index URIs
        This file is a Java properties file with rows likes this:
            nexus.index.incremental-15=526
            nexus.index.incremental-14=527

        Each value points to a fragment increamental index that has the same
        format as the bigger one.
        """

        base_url = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.{index}.gz'
        with open(content) as config_file:
            properties = javaproperties.load(config_file) or {}

        for key, increment_index in properties.items():
            if key.startswith('nexus.index.incremental'):
                yield URI(
                    uri=base_url.format(index=increment_index),
                    source_uri=self.uri,
                )


@visit_router.route(
    'https?://.*/nexus-maven-repository-index.gz',
    # increments
    'https?://.*/nexus-maven-repository-index\.\d+\.gz')
class MavenNexusIndexVisitor(NonPersistentHttpVisitor):
    """
    Download and process a Nexus Maven index file.
    WARNING: Processing is rather long: a full index is ~600MB.
    """

    def get_uris(self, content):
        """
        Yield a combo of pre-visited URIs with a special maven-index://
        scheme together with other regular fetchable URIs for POMs and
        JARs found in a Maven index.

        For NonPersistentHttpVisitor content is the path to the temp Gzipped
        index file, not the actual file content.
        """
        index_location = content

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
            if extension and extension != 'jar':
                qualifiers['type'] = extension

            classifier = artifact.classifier
            if classifier:
                qualifiers['classifier'] = classifier

            package_url = PackageURL(
                type='maven',
                namespace=group_id,
                name=artifact_id,
                version=version,
                qualifiers=qualifiers or None,
            )

            # FIXME: also use the Artifact.src_exist flags too?

            # build a URL: This is the real JAR download URL
            # FIXME: this should be set at the time of creating Artifacts
            # instead togther with the filename... especially we could use
            # different REPOs.
            jar_download_url, file_name = build_url_and_filename(
                group_id, artifact_id, version, extension, classifier)

            # FIXME: should this be set in the yielded URI too
            last_mod = artifact.last_modified

            # We yield a pre-visited URI for each JAR
            mock_maven_index_uri = build_url(
                group_id, artifact_id, version, file_name,
                base_url='maven-index://repo1.maven.org')

            artifact_data = artifact.to_dict()
            artifact_data['download_url'] = jar_download_url
            artifact_as_json = json.dumps(artifact_data, separators=(',', ':'))

            yield URI(
                # this is the Maven index index URI
                source_uri=self.uri,
                # FIXME: remove these mock URIs after migration
                uri=mock_maven_index_uri,
                package_url=package_url.to_string(),
                visited=True,
                mining_level=0,
                file_name=file_name,
                size=artifact.size,
                sha1=artifact.sha1,
                date=last_mod,
                data=artifact_as_json,
            )

            package_url = PackageURL(
                type='maven',
                namespace=group_id,
                name=artifact_id,
                version=version,
            )

            # also yield a POM for this. There are no artifacts for
            # the POM of a Jar in the repo. Only for Parent POMs
            # therefore we create a download with the pomextension
            pom_download_url, pom_file_name = build_url_and_filename(
                group_id, artifact_id, version, extension='pom', classifier='')
            yield URI(
                # this is the Maven index index URI
                source_uri=self.uri,
                uri=pom_download_url,
                # use the same PURL as the main jar
                package_url=package_url.to_string(),
                visited=False,
                mining_level=20,
                file_name=pom_file_name,
                size=0,
                date=last_mod,
            )


@visit_router.route('https?://jcenter\.bintray\.com/(.+/)*')
class MavenHTMLPageVisitor(HttpVisitor):
    """
    Parse the HTML page and yield all necessary uris from the page and its sub pages.
    Note that the regex of the route expression is using . to map any characters except new line is becasue of the case:
    http://jcenter.bintray.com/'com/virtualightning'/, this is in the test too.
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        for pre in page.find_all(name='pre'):
            for a in pre.find_all(name='a'):
                url = a.get('href')
                if not url:
                    continue
                if url.startswith(':'):  # Remove : symbol since it's a special char for bintray repo.
                    url = url[1:]
                filename = None  # default is folder, the filename is None.
                if not url.endswith('/'):
                    # a file
                    filename = url
                yield URI(
                    uri=self.uri + url,
                    visited=False,
                    file_name=filename,
                    source_uri=self.uri,
                )


@visit_router.route('https?://.*/maven-metadata\.xml')
class MavenMetaDataVisitor(HttpVisitor):
    """
    Parse the maven-metadata.xml file and yield uris of jars and pom.
    """

    def get_uris(self, content):
        # FIXME this may not be correct. The only thing we can infer from the maven
        # metadata is wha are the groupid/artifactid and available versions
        # The actual download files likely need to be obtained from directory listing
        # or infered from parsing the POM???

        base_url = self.uri.partition('maven-metadata.xml')[0] + '{version}/'
        pom_url = base_url + '{artifactId}-{version}.pom'

        # FIXME: this may not exist and or with another extension?? and this should be PREVISITED
        jar_url = base_url + '{artifactId}-{version}.jar'
        # FIXME: sources may not exists?? and this should be PREVISITED
        source_url = base_url + '{artifactId}-{version}-sources.jar'

        # FIXME: why use BeautifulSoup for valid XML???
        page = BeautifulSoup(content, 'lxml-xml')

        group_id = page.find(name='groupId')
        artifact_id = page.find(name='artifactId')
        if not (group_id and artifact_id):
            return

        group_id = group_id.string
        artifact_id = artifact_id.string

        for version in page.find_all('version'):
            version = version.string

            # FIXME: we may not get the proper extensions and classifiers and miss the qualifiers
            package_url = PackageURL(
                type='maven',
                namespace=group_id,
                name=artifact_id,
                version=version).to_string()

            # the JAR proper as previsited
            yield URI(
                source_uri=self.uri,
                uri=jar_url.format(version=version, artifactId=artifact_id),
                package_url=package_url,
                visited=True,
            )

            # the source as previsited
            yield URI(
                source_uri=self.uri,
                uri=source_url.format(version=version, artifactId=artifact_id),
                package_url=package_url,
                visited=True,
            )

            # the POM needs to be visited
            yield URI(
                source_uri=self.uri,
                uri=pom_url.format(version=version, artifactId=artifact_id),
                package_url=package_url,
                visited=False,
            )


# TODO: consider switching to HTTPS
def build_url_and_filename(group_id, artifact_id, version, extension, classifier,
                           base_repo_url='https://repo1.maven.org/maven2'):
    """
    Return a tuple of (url, filename) for the download URL of a Maven
    artifact built from its coordinates.
    """
    file_name = build_filename(artifact_id, version, extension, classifier)
    url = build_url(group_id, artifact_id, version, file_name, base_repo_url)
    return url, file_name


# TODO: consider switching to HTTPS
def build_maven_xml_url(group_id, artifact_id,
                        base_repo_url='https://repo1.maven.org/maven2'):
    """
    Return a download URL for a Maven artifact built from its
    coordinates.
    """
    group_id = group_id.replace('.', '/')
    path = '{group_id}/{artifact_id}'.format(**locals())
    return '{base_repo_url}/{path}/maven-metadata.xml'.format(**locals())


@visit_router.route('https?://repo1.maven.org/maven2/.*\.pom')
class MavenPOMVisitor(HttpVisitor):
    """
    Visit a POM. The POM XML is stored as data and there is nothing
    special to do for this visitor.
    """
    pass


def is_worthy_artifact(artifact):
    """
    We only care for certain artifacts that are worthy of indexing.

    Maven has some intricate interrelated values for these fields
        type, extension, packaging, classifier, language
    See http://maven.apache.org/ref/3.2.5/maven-core/artifact-handlers.html

    These are the defaults:

    type            extension   packaging    classifier   language
    --------------------------------------------------------------
    pom             = type      = type                    none
    jar             = type      = type                    java
    maven-plugin    jar         = type                    java
    ejb             jar         ejb = type                java
    ejb3            = type      ejb3 = type               java
    war             = type      = type                    java
    ear             = type      = type                    java
    rar             = type      = type                    java
    par             = type      = type                    java
    java-source     jar         = type        sources     java
    javadoc         jar         = type        javadoc     java
    ejb-client      jar         ejb           client      java
    test-jar        jar         jar           tests       java
    """
    if artifact.version == 'archetypes':
        # we skip these entirely, they have a different shape
        return

    worthy_ext_pack = set([
        # packaging, classifier, extension
        (u'jar', u'sources', u'jar'),
        (u'jar', None, u'jar'),
        (u'bundle', None, u'jar'),
        (u'war', None, u'war'),
        (u'zip', u'source-release', u'zip'),
        (u'maven-plugin', None, u'jar'),
        (u'aar', None, u'aar'),
        (u'jar', u'sources-commercial', u'jar'),
        (u'zip', u'src', u'zip'),
        (u'tar.gz', u'src', u'tar.gz'),
        (u'jar', None, u'zip'),
        (u'zip', u'project-src', u'zip'),
        (u'jar', u'src', u'jar'),
    ])

    return (artifact.packaging,
            artifact.classifier,
            artifact.extension,) in worthy_ext_pack


def is_source(classifier):
    """
    Return True if the `artifact` Artifact is a source artifact.

    """
    return classifier and ('source' in classifier or 'src' in classifier)


########################################################################
# DOCUMENTAION OF the FIELDS aka. Records:
#
# Constants and information for field names can be found in
# https://github.com/apache/maven-indexer/tree/ecddb3c18ee1ee1357a01bffa7f9cb5252f21209
# in these classes:
# - org.apache.maven.index.ArtifactInfoRecord
# - org.apache.maven.index.ArtifactInfo
# - org.apache.maven.index.creator.MinimalArtifactInfoIndexCreator
# See also org.apache.maven.index.reader
#
# Note: these are the field names found in the Maven central index in
# July 2016:
# i u 1 m n d del
# allGroups allGroupsList rootGroups rootGroupsList
# IDXINFO DESCRIPTOR
#
# Bundle-Description Bundle-DocURL Bundle-License Bundle-Name Bundle-
# SymbolicName Bundle-Version Export-Package Export-Service Import-
# Package Require-Bundle


ENTRY_FIELDS = {
    'u': 'Artifact UINFO: Unique groupId, artifactId, version, classifier, extension (or packaging). using',
    'i': 'Artifact INFO: data using | separator',
    '1': 'Artifact SHA1 checksum, hex encoded as in sha1sum',
    'm': 'Artifact record last modified, a long as a string representing a Java time for the entry record',
    'n': 'Artifact name',
    'd': 'Artifact description',
}

# we IGNORE these fields for now. They can be included optionally.
ENTRY_FIELDS_OTHER = {
    # rarely present, mostly is repos other than central
    'c': 'Artifact Classes (tokenized on newlines only) a list of LF-separated paths, without .class extension',

    'sha256': 'sha256 of artifact? part of OSGI?',

    # OSGI stuffs, not always there but could be useful metadata
    'Bundle-SymbolicName': 'Bundle-SymbolicName (indexed, stored)',
    'Bundle-Version': 'Bundle-Version (indexed, stored)',
    'Bundle-Description': 'Bundle-Description (indexed, stored)',
    'Bundle-Name': 'Bundle-Name (indexed, stored)',
    'Bundle-License': 'Bundle-License (indexed, stored)',
    'Bundle-DocURL': 'Bundle-DocURL (indexed, stored)',
    'Require-Bundle': 'Require-Bundle (indexed, stored)',
}

# we ignore these fields entirely for now.
ENTRY_FIELDS_IGNORED = {

    'IDXINFO': '',
    'DESCRIPTOR': '',

    'allGroups': '',
    'allGroupsList': '',
    'rootGroups': '',
    'rootGroupsList': '',

    # FIXME: we should deal with these
    'del': 'Deleted marker, will contain UINFO if document is deleted from index',

    'Export-Package': 'Export-Package (indexed, stored)',
    'Export-Service': 'Export-Service (indexed, stored)',
    'Import-Package': 'Import-Package (indexed, stored)',
    # maven-plugin stuffs
    'px': 'MavenPlugin prefix (as keyword, stored)',
    'gx': 'MavenPlugin goals (as keyword, stored)',
}


def get_artifacts(location, fields=frozenset(ENTRY_FIELDS),
                  worthyness=is_worthy_artifact, include_all=False):
    """
    Yield artifact mappings from a Gzipped Maven nexus index data file
    at location.
    """
    for entry in get_entries(location, fields):
        artifact = build_artifact(entry, include_all)
        # at this stage we know enough to decide is this data is worthy of being an
        # artifact for now we care only about a few things: POMs and binary Jars.
        if artifact and worthyness(artifact):
            yield artifact


_artifact_base_fields = (
    'group_id',
    'artifact_id',
    'version',
    'packaging',
    'classifier',
    'extension',
    'last_modified',
    'size',
    'sha1',
    'name',
    'description',
    'src_exist',
    'jdoc_exist',
    'sig_exist',
)

_artifact_extended_fields = (
    'sha256',
    'osgi',
    'classes',
)

# FIXME: named tuples are suboptimal here for a simple dictionary


def to_dict(self):
    return self._asdict()


Artifact = namedtuple('Artifact', _artifact_base_fields)
Artifact.to_dict = to_dict

ArtifactExtended = namedtuple('ArtifactExtended', _artifact_base_fields + _artifact_extended_fields)
ArtifactExtended.to_dict = to_dict


def build_artifact(entry, include_all=False):
    """
    Return a Maven artifact mapping collected from a single entry
    mapping or None.
    """

    SEP = '|'
    NA = 'NA'
    NULL = 'null'

    # UINFO
    # See org.apache.maven.index.reader.RecordExpander.expandUinfo
    # See org.apache.maven.index.creator.MinimalArtifactInfoIndexCreator.updateArtifactInfo
    uinfo = entry.get('u')
    if not uinfo:
        # not much we can do without this
        return

    uinfo = uinfo.split(SEP)
    gid = uinfo[0]
    aid = uinfo[1]
    version = uinfo[2]

    classifier = uinfo[3]
    if classifier == NA:
        classifier = None

    extension = None
    if len(uinfo) > 4:
        extension = uinfo[4]

    # INFO
    # See org.apache.maven.index.reader.RecordExpander.expandAddedArtifact
    # See org.apache.maven.index.creator.MinimalArtifactInfoIndexCreator.updateArtifactInfo

    packaging = None
    size = 0
    # record last modified is at entry.get('m') and we ignore this
    last_modified = None
    src_exist = False
    jdoc_exist = False
    sig_exist = False

    info = entry.get('i')
    if info:
        info = info.split(SEP)

        packaging = info[0]
        if packaging in (NA, NULL):
            packaging = None

        # this is the artifact last modified
        # create a date/time stamp string from a long as a string
        lm = info[1]
        if lm and lm.isdigit() and lm != '0':
            last_modified = java_time_ts(int(lm))

        size = info[2]
        size = int(size) if size and size.isdigit() else None

        # for *Exists fields of INFO: see org.apache.maven.index.ArtifactAvailability
        # not present locally: '0': False,
        # present locally: '1': True, ==> the only one we care for
        # not available: '2': False,
        PRESENT = '1'
        src_exist = info[3] == PRESENT
        jdoc_exist = info[4] == PRESENT

        if len(info) > 6:
            extension = info[6]
        else:
            # FIXME: is this likely incorrect see worthyness check
            if classifier or packaging in ('pom', 'war', 'ear'):
                extension = packaging
            else:
                extension = 'jar'
        sig_exist = info[5] == PRESENT

    # other MISC fields
    sha1 = entry.get('1')
    name = entry.get('n')
    description = entry.get('d')

    if not include_all:
        artifact = Artifact(
            group_id=gid, artifact_id=aid, version=version,
            packaging=packaging, classifier=classifier, extension=extension,
            last_modified=last_modified, size=size, sha1=sha1,
            name=name, description=description,
            src_exist=src_exist, jdoc_exist=jdoc_exist, sig_exist=sig_exist,
        )

    else:
        # TODO: should this be part of the base set?
        sha256 = entry.get('sha256')

        # OSGI: Rarely there. Note that we ignore 'Export-', 'Import-', on
        # purpose: these are big and messey for now
        osgi = dict()
        for key, value in entry.items():
            if key.startswith('Bundle-') and value:
                # TODO: could also include 'Require-Bundle'
                osgi[key] = value.strip()

        # Classes: Rarely there, but eventually useful in the future
        # Can be quite big too
        classes = entry.get('c', '').splitlines(False)

        artifact = ArtifactExtended(
            group_id=gid, artifact_id=aid, version=version,
            packaging=packaging, classifier=classifier, extension=extension,
            last_modified=last_modified, size=size, sha1=sha1,
            name=name, description=description,
            src_exist=src_exist, jdoc_exist=jdoc_exist, sig_exist=sig_exist,
            sha256=sha256, osgi=osgi, classes=classes
        )

    return artifact


def get_entries(location, fields=frozenset(ENTRY_FIELDS)):
    """
    Yield Maven index entry mappings from a Gzipped Maven nexus index
    data file at `location`. Only includes `fields` names.
    """
    buffer_size = 128 * 1024 * 1024
    if TRACE_DEEP:
        entry = None
        entries_count = 0
        keys = set()
        keys_update = keys.update

    with GzipFileWithTrailing(location, 'rb') as compressed:
        # using io.BufferedReader for increased perfs
        with io.BufferedReader(compressed, buffer_size=buffer_size) as nexus_index:
            jstream = java_stream.DataInputStream(nexus_index)

            # FIXME: we do nothing with these two
            # NOTE: this reads 1+8=9 bytes of the stream
            _index_version, _last_modified = decode_index_header(jstream)
            while True:
                try:
                    entry = decode_entry(jstream, fields)
                    if TRACE_DEEP:
                        if entry:
                            keys_update(entry)
                        entries_count += 1

                    if entry:
                        yield entry

                except EOFError:
                    if TRACE_DEEP:
                        print('Index version: %(_index_version)r last_modified: %(_last_modified)r' % locals())
                        print('Processed %(entries_count)d docs. Last entry: %(entry)r' % locals())
                        print('Unique keys:')
                        for k in sorted(keys):
                            print(k)
                    break


def decode_index_header(jstream):
    """
    Return the index header from a `jstream` Java-like stream as a tuple
    of (index_version, last_updated_date) where index_version is an int
    and last_updated_date is a an UTC ISO timestamp string or an empty
    string.
    """

#     this.chunkName = chunkName.trim();
#     this.dataInputStream = new DataInputStream( new GZIPInputStream( inputStream, 2 * 1024 ) );
#     this.version = ( (int) dataInputStream.readByte() ) & 0xff;
#     this.timestamp = new Date( dataInputStream.readLong() );

    supported_format_version = 1
    # one byte
    index_version = int(jstream.read_byte())
    assert supported_format_version == index_version
    # eight byte
    timestamp = jstream.read_long()
    last_modified = timestamp != -1 and java_time_ts(timestamp) or ''
    return int(index_version), last_modified


def decode_entry(jstream, fields=()):
    """
    Read and return one entry mapping of name -> values from a Maven
    index `jstream` Java-like stream. Note that the stream is not a
    standard Java stream for UTF data.

    Only includes `fields` names.

    An entry starts with an integer which is the number of fields for
    this entry.

    Then we have this data layout for each field:

     - field storage type: one byte flag which is then compared to
       constants. These are flags for Lucene indexing: INDEXED, STORED,
       TOKENIZED, ANALYZED it ends up being two booleans: indexed and
       stored and we do not care for these.

     - field name: a Java UTF-8 string (using a len on 2 bytes, then the
       name proper). Constants for field names are in ArtifactInfoRecord
       and ArtifactInfo. The entry for these is available in ENTRY_FIELDS
       for reference.

     - field value: a Java UTF-8-encoded string using the Maven Index special encoding
       - one int which is the length of the UTF string in bytes
       - the utf-8 string proper using Java conventions
    """

    read = jstream.read
    read_int = jstream.read_int
    read_byte = jstream.read_byte
    read_utf = jstream.read_utf

    has_fields = bool(fields)
    entry = {}
    # this read 4 bytes
    field_count = read_int()
    for _ in range(field_count):
        # Flags for lucene: INDEXED, STORED, TOKENIZED, ANALYZED: ignored
        # this is a mask and one off:
        # field_indexed = 1
        # field_tokenized = 2
        # field_stored = 4
        # this reads 1 byte: total 5
        _indexing_type = read_byte()

        # all field names are ASCII chars, so even though this is UTF-8
        # encoded, this is ascii Constants for field names are in
        # ArtifactInfoRecord and ArtifactInfo
        # FIXME: we should discard things we do not care for in terms of fields right away

        # Read a regular "Java Modified UTF-8" as unicode.
        # this read 2 bytes which are the len then the len. total 7 + len
        name = decode_modified_utf8(read_utf())

        # Read a Maven Nexus index special "Java Modified UTF-8" as
        # unicode: Regular Java write/readUTF is a string length on 2
        # bytes followed by a UTF-encoded stream of bytes of that
        # length. The Nexus Maven index use a full int rather than a 2
        # bytes int bypassing the 65K char limit for length of the
        # standard Java readUTF.
        # this read 4 bytes which is a len
        value_length = read_int()
        # this read bytes len
        value = decode_modified_utf8(read(value_length))

        # why do we skip some fields
        if has_fields:
            if name in fields:
                entry[name] = value
        else:
            entry[name] = value

    return entry


def java_time_ts(tm):
    """
    Convert a Java time long (as milliseconds since epoch) to an UTC ISO
    timestamp.
    """
    tzinfo = tz.tzutc()
    ar = arrow.get(tm / 1000).replace(tzinfo=tzinfo).to('utc')
    return ar.isoformat()


################################################################################
# These are CLI/shell test and stat utilities
################################################################################

def _spit_json(location, target):
    with open(target, 'w') as t:
        t.write('[\n')
        for i, artifact in enumerate(get_artifacts(location)):
            if i % 1000 == 0:
                print('number or artifacts:', i)
            t.write(json.dumps(artifact.to_dict(), separators=(',', ':')))
            t.write(',\n')

        t.write(']\n')

    print('total number or artifacts:', i)


def _artifact_stats(location):
    """
    Print artifacts stats from a Gzipped Maven nexus index data file
    at location.
    """
    from collections import Counter
    pom_packs = Counter()
    pom_classifs = Counter()
    pom_extensions = Counter()
    combos = Counter()

    pom_worthy = 0

    for i, artifact in enumerate(get_artifacts(location)):
        combos[(artifact.packaging, artifact.classifier, artifact.extension)] += 1

        if artifact.packaging:
            pom_packs[artifact.packaging] += 1

        if artifact.classifier:
            pom_classifs[artifact.classifier] += 1

        if artifact.extension:
            pom_extensions[artifact.extension] += 1

        if is_worthy_artifact(artifact):
            pom_worthy += 1

        if i % 10000 == 0:
            print('number or artifacts:', i)

    print()
    print('Total number of artifacts:', i)
    print('Total number of worthy artifacts:', pom_worthy)

    print('Top packaging:')
    for n, c in pom_packs.most_common():
        print(n, ":", c)

    print('Top classifiers:')
    for n, c in pom_classifs.most_common():
        print(n, ":", c)

    print('Top extensions:')
    for n, c in pom_extensions.most_common():
        print(n, ":", c)

    print('Top Combos: packaging, classifier, extension')
    for n, c in combos.most_common():
        print(n, ":", c)

    """
    Latest stats on 2017-08-07:
Total number or artifacts: 5844648
Total number of POMs: 302603
Total number of worthy POMs: 300879
Total number of JARs: 5158191
Total number of POMs with names: 278521 with description: 151034
Total number of JARs with names: 4762013 with description: 3144938
Total number of Other with names: 360646 with description: 228119
Unique POM packagings: [None, u'${packaging.type}', u'${packagingType}',
    u'0-alpha-1-20050407.154541-1.pom', u'aar', u'apk', u'application-assembly',
    u'bundle', u'feature', u'gem', u'hk2-jar', u'it-packaging', u'izpack-jar',
    u'jar', u'jboss-sar', u'maven-archetype', u'maven-plugin', u'mule-extension',
    u'mule-plugin', u'nar', u'nbm-application', u'pom', u'so', u'swc', u'tar',
    u'tar.gz', u'war', u'xar', u'zip']
Unique POM classifiers: [None, u'1', u'DEAD', u'M6a', u'bsd', u'changelog',
u'dtddoc', u'it', u'java', u'javadoc', u'jdbc3', u'pom']
    """


def _entries_stats(location):
    """
    Print entries stats from a Gzipped Maven nexus index data file
    at location.
    """
    from collections import Counter
    field_names = Counter()
    field_names_update = field_names.update

    field_sets = Counter()
    field_sets_update = field_sets.update

    for i, entry in enumerate(get_entries(location, ())):
        keys = tuple(entry.keys())
        field_names_update(keys)
        field_sets_update([keys])
        if i % 10000 == 0:
            print()
            print('number of entries:', i)
            print('field names stats:', field_names)

    print()
    print('Total number of entries:', i)
    print()
    print('All field names:', field_names.most_common())
    print()
    print('All field name sets:', field_sets.most_common())
    print()
