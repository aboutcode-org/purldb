#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import re
import requests
import os
import gzip
import io
import logging
import arrow
from aboutcode import hashid
from packageurl import PackageURL
from urllib.parse import urlparse
from dateutil import tz
from minecode_pipeline.pipes import java_stream
from collections import namedtuple
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes import federatedcode
from jawa.util.utf import decode_modified_utf8
from packagedcode.maven import get_urls
from packagedcode.maven import build_filename
from packagedcode.maven import build_url
from packagedcode.models import PackageData

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRACE = False
TRACE_DEEP = False

if TRACE:
    import sys

    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


MAVEN_BASE_URL = "https://repo1.maven.org/maven2"
MAVEN_INDEX_URL = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"


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
    if artifact.version == "archetypes":
        # we skip these entirely, they have a different shape
        return

    worthy_ext_pack = set(
        [
            # packaging, classifier, extension
            ("jar", "sources", "jar"),
            ("jar", None, "jar"),
            ("bundle", None, "jar"),
            ("war", None, "war"),
            ("zip", "source-release", "zip"),
            ("maven-plugin", None, "jar"),
            ("aar", None, "aar"),
            ("jar", "sources-commercial", "jar"),
            ("zip", "src", "zip"),
            ("tar.gz", "src", "tar.gz"),
            ("jar", None, "zip"),
            ("zip", "project-src", "zip"),
            ("jar", "src", "jar"),
        ]
    )

    return (
        artifact.packaging,
        artifact.classifier,
        artifact.extension,
    ) in worthy_ext_pack


def is_source(classifier):
    """Return True if the `artifact` Artifact is a source artifact."""
    return classifier and ("source" in classifier or "src" in classifier)


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
    "u": "Artifact UINFO: Unique groupId, artifactId, version, classifier, extension (or packaging). using",
    "i": "Artifact INFO: data using | separator",
    "1": "Artifact SHA1 checksum, hex encoded as in sha1sum",
    "m": "Artifact record last modified, a long as a string representing a Java time for the entry record",
    "n": "Artifact name",
    "d": "Artifact description",
}

# we IGNORE these fields for now. They can be included optionally.
ENTRY_FIELDS_OTHER = {
    # rarely present, mostly is repos other than central
    "c": "Artifact Classes (tokenized on newlines only) a list of LF-separated paths, without .class extension",
    "sha256": "sha256 of artifact? part of OSGI?",
    # OSGI stuffs, not always there but could be useful metadata
    "Bundle-SymbolicName": "Bundle-SymbolicName (indexed, stored)",
    "Bundle-Version": "Bundle-Version (indexed, stored)",
    "Bundle-Description": "Bundle-Description (indexed, stored)",
    "Bundle-Name": "Bundle-Name (indexed, stored)",
    "Bundle-License": "Bundle-License (indexed, stored)",
    "Bundle-DocURL": "Bundle-DocURL (indexed, stored)",
    "Require-Bundle": "Require-Bundle (indexed, stored)",
}

# we ignore these fields entirely for now.
ENTRY_FIELDS_IGNORED = {
    "IDXINFO": "",
    "DESCRIPTOR": "",
    "allGroups": "",
    "allGroupsList": "",
    "rootGroups": "",
    "rootGroupsList": "",
    # FIXME: we should deal with these
    "del": "Deleted marker, will contain UINFO if document is deleted from index",
    "Export-Package": "Export-Package (indexed, stored)",
    "Export-Service": "Export-Service (indexed, stored)",
    "Import-Package": "Import-Package (indexed, stored)",
    # maven-plugin stuffs
    "px": "MavenPlugin prefix (as keyword, stored)",
    "gx": "MavenPlugin goals (as keyword, stored)",
}


def get_artifacts(
    location,
    fields=frozenset(ENTRY_FIELDS),
    worthyness=is_worthy_artifact,
    include_all=False,
):
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


def get_artifacts2(
    location,
    fields=frozenset(ENTRY_FIELDS),
    worthyness=is_worthy_artifact,
    include_all=False,
):
    """
    Yield artifact mappings from a Gzipped Maven nexus index data file
    at location.
    """
    print(get_entries2(location, fields))


_artifact_base_fields = (
    "group_id",
    "artifact_id",
    "version",
    "packaging",
    "classifier",
    "extension",
    "last_modified",
    "size",
    "sha1",
    "name",
    "description",
    "src_exist",
    "jdoc_exist",
    "sig_exist",
)

_artifact_extended_fields = (
    "sha256",
    "osgi",
    "classes",
)

# FIXME: named tuples are suboptimal here for a simple dictionary


def to_dict(self):
    return self._asdict()


Artifact = namedtuple("Artifact", _artifact_base_fields)
Artifact.to_dict = to_dict

ArtifactExtended = namedtuple("ArtifactExtended", _artifact_base_fields + _artifact_extended_fields)
ArtifactExtended.to_dict = to_dict


def build_artifact(entry, include_all=False):
    """
    Return a Maven artifact mapping collected from a single entry
    mapping or None.
    """
    SEP = "|"
    NA = "NA"
    NULL = "null"

    # UINFO
    # See org.apache.maven.index.reader.RecordExpander.expandUinfo
    # See org.apache.maven.index.creator.MinimalArtifactInfoIndexCreator.updateArtifactInfo
    uinfo = entry.get("u")
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

    info = entry.get("i")
    if info:
        info = info.split(SEP)

        packaging = info[0]
        if packaging in (NA, NULL):
            packaging = None

        # this is the artifact last modified
        # create a date/time stamp string from a long as a string
        lm = info[1]
        if lm and lm.isdigit() and lm != "0":
            last_modified = java_time_ts(int(lm))

        size = info[2]
        size = int(size) if size and size.isdigit() else None

        # for *Exists fields of INFO: see org.apache.maven.index.ArtifactAvailability
        # not present locally: '0': False,
        # present locally: '1': True, ==> the only one we care for
        # not available: '2': False,
        PRESENT = "1"
        src_exist = info[3] == PRESENT
        jdoc_exist = info[4] == PRESENT

        if len(info) > 6:
            extension = info[6]
        else:
            # FIXME: is this likely incorrect see worthyness check
            if classifier or packaging in ("pom", "war", "ear"):
                extension = packaging
            else:
                extension = "jar"
        sig_exist = info[5] == PRESENT

    # other MISC fields
    sha1 = entry.get("1")
    name = entry.get("n")
    description = entry.get("d")

    if not include_all:
        artifact = Artifact(
            group_id=gid,
            artifact_id=aid,
            version=version,
            packaging=packaging,
            classifier=classifier,
            extension=extension,
            last_modified=last_modified,
            size=size,
            sha1=sha1,
            name=name,
            description=description,
            src_exist=src_exist,
            jdoc_exist=jdoc_exist,
            sig_exist=sig_exist,
        )

    else:
        # TODO: should this be part of the base set?
        sha256 = entry.get("sha256")

        # OSGI: Rarely there. Note that we ignore 'Export-', 'Import-', on
        # purpose: these are big and messey for now
        osgi = dict()
        for key, value in entry.items():
            if key.startswith("Bundle-") and value:
                # TODO: could also include 'Require-Bundle'
                osgi[key] = value.strip()

        # Classes: Rarely there, but eventually useful in the future
        # Can be quite big too
        classes = entry.get("c", "").splitlines(False)

        artifact = ArtifactExtended(
            group_id=gid,
            artifact_id=aid,
            version=version,
            packaging=packaging,
            classifier=classifier,
            extension=extension,
            last_modified=last_modified,
            size=size,
            sha1=sha1,
            name=name,
            description=description,
            src_exist=src_exist,
            jdoc_exist=jdoc_exist,
            sig_exist=sig_exist,
            sha256=sha256,
            osgi=osgi,
            classes=classes,
        )

    return artifact


class GzipFileWithTrailing(gzip.GzipFile):
    """
    A subclass of gzip.GzipFile supporting files with trailing garbage. Ignore
    the garbage.
    """

    # TODO: what is first_file??
    first_file = True
    gzip_magic = b"\037\213"
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
            raise EOFError("Trailing garbage found")

        self.first_file = False
        gzip.GzipFile._read_gzip_header(self)


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

    with GzipFileWithTrailing(location, "rb") as compressed:
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
                        print(f"Index version: {_index_version} last_modified: {_last_modified}")
                        print(f"Processed {entries_count} docs. Last entry: {entry}")
                        print("Unique keys:")
                        for k in sorted(keys):
                            print(k)
                    break


def get_entries2(location, fields=frozenset(ENTRY_FIELDS)):
    """
    Return Maven index entry mappings from a Gzipped Maven nexus index
    data file at `location`. Only includes `fields` names.
    """
    buffer_size = 128 * 1024 * 1024
    entry = None
    entries_count = 0
    keys = set()
    keys_update = keys.update

    with GzipFileWithTrailing(location, "rb") as compressed:
        # using io.BufferedReader for increased perfs
        with io.BufferedReader(compressed, buffer_size=buffer_size) as nexus_index:
            jstream = java_stream.DataInputStream(nexus_index)

            # FIXME: we do nothing with these two
            # NOTE: this reads 1+8=9 bytes of the stream
            _index_version, _last_modified = decode_index_header(jstream)
            while True:
                try:
                    entry = decode_entry(jstream, fields)
                    if entry:
                        keys_update(entry)
                    entries_count += 1

                except EOFError:
                    if TRACE_DEEP:
                        print(f"Index version: {_index_version} last_modified: {_last_modified}")
                        print(f"Processed {entries_count} docs. Last entry: {entry}")
                        print("Unique keys:")
                        for k in sorted(keys):
                            print(k)
                    break
    return keys


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
    last_modified = timestamp != -1 and java_time_ts(timestamp) or ""
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
    ar = arrow.get(tm / 1000).replace(tzinfo=tzinfo).to("utc")
    return ar.isoformat()


# TODO: consider switching to HTTPS
def build_url_and_filename(
    group_id,
    artifact_id,
    version,
    extension,
    classifier,
    base_repo_url="https://repo1.maven.org/maven2",
):
    """
    Return a tuple of (url, filename) for the download URL of a Maven
    artifact built from its coordinates.
    """
    file_name = build_filename(artifact_id, version, extension, classifier)
    url = build_url(group_id, artifact_id, version, file_name, base_repo_url)
    return url, file_name


# TODO: consider switching to HTTPS
def build_maven_xml_url(group_id, artifact_id, base_repo_url="https://repo1.maven.org/maven2"):
    """
    Return a download URL for a Maven artifact built from its
    coordinates.
    """
    group_id = group_id.replace(".", "/")
    path = "{group_id}/{artifact_id}".format(**locals())
    return "{base_repo_url}/{path}/maven-metadata.xml".format(**locals())


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
        index = fetch_http(uri)
        return index.path

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

    def get_packages2(self, content=None):
        """Yield Package objects from maven index"""
        if content:
            index_location = content
        else:
            index_location = self.fetch_index()

        get_artifacts2(index_location, worthyness=is_worthy_artifact)


###############################################################################


collect_links = re.compile(r'href="([^"]+)"').findall
collect_links_and_artifact_timestamps = re.compile(
    r'<a href="([^"]+)".*</a>\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|-)'
).findall


def check_if_file_name_is_linked_on_page(file_name, links, **kwargs):
    """Return True if `file_name` is in `links`"""
    return any(link.endswith(file_name) for link in links)


def check_if_page_has_pom_files(links, **kwargs):
    """Return True of any entry in `links` ends with .pom."""
    return any(link.endswith(".pom") for link in links)


def check_if_page_has_directories(links, **kwargs):
    """Return True if any entry, excluding "../", ends with /."""
    return any(link.endswith("/") for link in links if link != "../")


def check_if_package_version_page(links, **kwargs):
    """Return True if `links` contains pom files and has no directories"""
    return check_if_page_has_pom_files(links=links) and not check_if_page_has_directories(
        links=links
    )


def check_if_package_page(links, **kwargs):
    return check_if_file_name_is_linked_on_page(
        file_name="maven-metadata.xml", links=links
    ) and not check_if_page_has_pom_files(links=links)


def check_if_maven_root(links, **kwargs):
    """
    Return True if "archetype-catalog.xml" is in `links`, as the root of a Maven
    repo contains "archetype-catalog.xml".
    """
    return check_if_file_name_is_linked_on_page(file_name="archetype-catalog.xml", links=links)


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


def get_package_versions(url):
    """
    Given a `url` to a maven package page, return a list of the available package versions
    """
    versions = []
    response = requests.get(url)
    if response:
        links = collect_links(response.text)
        # filter for directories, skipping "../" and files
        # each directory name is a package version
        versions = [link for link in links if link.endswith("/") and link != "../"]
        # remove trailing / from version
        versions = [v.rstrip("/") for v in versions]
    return versions


def validate_sha1(sha1):
    """
    Validate a `sha1` string.

    Return `sha1` if it is valid, None otherwise.
    """
    if sha1 and len(sha1) != 40:
        logger.warning(f'Invalid SHA1 length ({len(sha1)}): "{sha1}": SHA1 ignored!')
        sha1 = None
    return sha1


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


def crawl_to_package(url, root_url):
    """
    Given a maven repo `url`, crawl the repo and for each package, yield a
    PackageURL and a list of PackageURLs of available versions
    """
    if is_package_page(url):
        namespace, name, _ = determine_namespace_name_version_from_url(url)
        versions = get_package_versions(url)
        purl = PackageURL(type="maven", namespace=namespace, name=name)
        purls = [
            PackageURL(
                type="maven",
                namespace=namespace,
                name=name,
                version=version,
            )
            for version in versions
        ]
        yield purl, purls

    for link in get_directory_links(url):
        crawl_to_package(link, root_url)


def crawl_maven_repo_from_root(root_url):
    """
    Given the `url` to a maven root, traverse the repo depth-first and add
    packages to the import queue.
    """
    crawl_to_package(root_url, root_url)


def collect_packages_from_maven(project, logger):
    for purl, purls in crawl_maven_repo_from_root():
        # check out repo
        repo = federatedcode.clone_repository(
            repo_url="",
            logger=logger,
        )
        # save purls to yaml
        ppath = hashid.get_package_purls_yml_file_path(purl)
        federatedcode.write_file(
            base_path=repo.working_dir,
            file_path=ppath,
            data=purls,
        )
        # commit and push
        federatedcode.commit_and_push_changes(
            repo=repo,
            file_to_commit=ppath,
            purl=purl,
            logger=logger,
        )
