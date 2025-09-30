#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import namedtuple
from itertools import chain
from shutil import rmtree
import os
import gzip
import io

from dateutil import tz
from jawa.util.utf import decode_modified_utf8
import arrow
import javaproperties

from aboutcode import hashid
from packagedcode.maven import build_filename
from packagedcode.maven import build_url
from packagedcode.maven import get_urls
from packagedcode.models import PackageData
from packageurl import PackageURL
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes import federatedcode

from minecode_pipelines import pipes
from minecode_pipelines import VERSION
from minecode_pipelines.pipes import java_stream

TRACE = False
TRACE_DEEP = False

MAVEN_BASE_URL = "https://repo1.maven.org/maven2"
MAVEN_INDEX_URL = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"
MAVEN_INDEX_INCREMENT_BASE_URL = (
    "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.{index}.gz"
)
MAVEN_INDEX_PROPERTIES_URL = (
    "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties"
)
MAVEN_CHECKPOINT_PATH = "maven/checkpoints.json"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_MAVEN_REPO = "https://github.com/aboutcode-data/minecode-data-maven-test"

PACKAGE_BATCH_SIZE = 500


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

    def __init__(self, index_location=None, index_properties_location=None, last_incremental=None):
        if index_location and last_incremental:
            raise Exception(
                "index_location and last_incremental cannot both be set at the same time. "
                "MavenNexusCollector() is only able to yield packages from a maven index or "
                "packages starting past a particular index increment."
            )

        self.downloads = []

        if index_properties_location:
            self.index_properties_location = index_properties_location
        else:
            index_property_download = self._fetch_index_properties()
            self.index_properties_location = index_property_download.path

        if self.index_properties_location:
            with open(self.index_properties_location) as config_file:
                self.index_properties = javaproperties.load(config_file) or {}
        else:
            self.index_properties = {}

        if last_incremental:
            self.index_location = None
            index_increment_downloads = self._fetch_index_increments(
                last_incremental=last_incremental
            )
            self.index_increment_locations = [
                download.path for download in index_increment_downloads
            ]
        elif index_location:
            self.index_location = index_location
            self.index_increment_locations = []
        else:
            index_download = self._fetch_index()
            self.index_location = index_download.path
            self.index_increment_locations = []

    def __del__(self):
        if self.downloads:
            for download in self.downloads:
                rmtree(download.directory)

    def _fetch_http(self, uri):
        fetched = fetch_http(uri)
        self.downloads.append(fetched)
        return fetched

    def _fetch_index(self, uri=MAVEN_INDEX_URL):
        """
        Fetch the maven index at `uri` and return a Download with information
        about where it was saved.
        """
        index = self._fetch_http(uri)
        return index

    def _fetch_index_properties(self, uri=MAVEN_INDEX_PROPERTIES_URL):
        """
        Fetch the maven index properties file at `uri` and return a Download
        with information about where it was saved.
        """
        index_properties = self._fetch_http(uri)
        return index_properties

    def _fetch_index_increments(self, last_incremental):
        """
        Fetch maven index increments, starting past `last_incremental`, and
        return a list of Downloads with information about where they were saved.
        """
        index_increment_downloads = []
        for key, increment_index in self.index_properties.items():
            if increment_index <= last_incremental:
                continue
            if key.startswith("nexus.index.incremental"):
                index_increment_url = MAVEN_INDEX_INCREMENT_BASE_URL.format(index=increment_index)
                index_increment = self._fetch_http(index_increment_url)
                index_increment_downloads.append(index_increment)
        return index_increment_downloads

    def _get_packages(self, content=None):
        artifacts = get_artifacts(content, worthyness=is_worthy_artifact)

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

            package = PackageData(
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
            current_purl = PackageURL(
                type="maven",
                namespace=group_id,
                name=artifact_id,
                version=version,
            )
            yield current_purl, package

    def _get_packages_from_index_increments(self):
        for index_increment in self.index_increment_locations:
            yield self._get_packages(content=index_increment)

    def get_packages(self):
        """Yield Package objects from maven index or index increments"""
        if self.index_increment_locations:
            packages = chain(self._get_packages_from_index_increments())
        else:
            packages = self._get_packages(content=self.index_location)
        return packages


def collect_packages_from_maven(commits_per_push=PACKAGE_BATCH_SIZE, logger=None):
    # Clone data and config repo
    data_repo = federatedcode.clone_repository(
        repo_url=MINECODE_DATA_MAVEN_REPO,
        logger=logger,
    )
    config_repo = federatedcode.clone_repository(
        repo_url=pipes.MINECODE_PIPELINES_CONFIG_REPO,
        logger=logger,
    )
    if logger:
        logger(f"{MINECODE_DATA_MAVEN_REPO} repo cloned at: {data_repo.working_dir}")
        logger(f"{pipes.MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {config_repo.working_dir}")

    # get last_incremental to see if we can start from incrementals
    checkpoint = pipes.get_checkpoint_from_file(cloned_repo=config_repo, path=MAVEN_CHECKPOINT_PATH)
    last_incremental = checkpoint.get("last_incremental")
    if logger:
        logger(f"last_incremental: {last_incremental}")

    # download and iterate through maven nexus index
    maven_nexus_collector = MavenNexusCollector(last_incremental=last_incremental)
    prev_purl = None
    current_purls = []
    for i, (current_purl, package) in enumerate(maven_nexus_collector.get_packages(), start=1):
        if not prev_purl:
            prev_purl = current_purl
        elif prev_purl != current_purl:
            # write packageURLs to file
            package_base_dir = hashid.get_package_base_dir(purl=prev_purl)
            purl_file = pipes.write_packageurls_to_file(
                repo=data_repo,
                base_dir=package_base_dir,
                packageurls=current_purls,
            )

            # commit changes
            federatedcode.commit_changes(
                repo=data_repo,
                files_to_commit=[purl_file],
                purls=current_purls,
                mine_type="packageURL",
                tool_name="pkg:pypi/minecode-pipelines",
                tool_version=VERSION,
            )

            # Push changes to remote repository
            push_commit = not bool(i % commits_per_push)
            if push_commit:
                federatedcode.push_changes(repo=data_repo)

            current_purls = []
            prev_purl = current_purl
        current_purls.append(package.purl)

    if current_purls:
        # write packageURLs to file
        package_base_dir = hashid.get_package_base_dir(purl=prev_purl)
        purl_file = pipes.write_packageurls_to_file(
            repo=data_repo,
            base_dir=package_base_dir,
            packageurls=current_purls,
        )

        # commit changes
        federatedcode.commit_changes(
            repo=data_repo,
            files_to_commit=[purl_file],
            purls=current_purls,
            mine_type="packageURL",
            tool_name="pkg:pypi/minecode-pipelines",
            tool_version=VERSION,
        )

        # Push changes to remote repository
        federatedcode.push_changes(repo=data_repo)

    # update last_incremental so we can pick up from the proper place next time
    last_incremental = maven_nexus_collector.index_properties.get("nexus.index.last-incremental")
    checkpoint = {"last_incremental": last_incremental}
    if logger:
        logger(f"checkpoint: {checkpoint}")
    pipes.update_checkpoints_in_github(
        checkpoint=checkpoint, cloned_repo=config_repo, path=MAVEN_CHECKPOINT_PATH
    )

    repos_to_clean = [data_repo, config_repo]
    return repos_to_clean
