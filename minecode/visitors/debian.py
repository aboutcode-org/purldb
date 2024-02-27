#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import attr
import gzip
import json
import logging
import requests

from commoncode import fileutils
import debian_inspector
from debian_inspector import debcon
from debian_inspector import copyright as debcopy
from debian_inspector.version import Version as DebVersion
from packagedcode.models import PackageData
from packagedcode.debian import DebianDscFileHandler
from packageurl import PackageURL

from minecode import ls
from minecode import seed
from minecode import visit_router
from minecode import priority_router
from minecode.visitors import HttpVisitor
from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import URI
from minecode.utils import get_temp_dir
from minecode.utils import get_temp_file
from minecode.utils import get_package_sha1
from packagedb.models import make_relationship
from packagedb.models import PackageContentType
from packagedb.models import PackageRelation

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

"""
Collect Debian and Debian derivative packages (such as Ubuntu).
There are two approaches:
1. get the directory listings of all available packages (and files)
2. get and navigate through the tree of Debian control files
"""


DEBIAN_BASE_URL = "https://deb.debian.org/debian/pool/main/"
DEBIAN_METADATA_URL = "https://metadata.ftp-master.debian.org/changelogs/main/"
# Other URLs and sources to consider
# 'http://ftp.debian.org/debian/'
# rsync://archive.debian.org/debian-archive
# http://sources.debian.net/doc/api/
# Packages.gz files: https://get.videolan.org/debian/i386/Packages.gz
# https://debian-handbook.info/browse/stable/sect.setup-apt-package-repository.html


class DebianSeed(seed.Seeder):

    def get_seeds(self):
        yield 'http://ftp.debian.org/debian/ls-lR.gz'
        yield 'http://archive.ubuntu.com/ubuntu/ls-lR.gz'


def is_collectible(file_name):
    """
    Return True if a `file_name` is collectible.
    """
    # 'Contents-*.gz' are mapping/indexes of installed files to the actual package that provides them.
    # TODO: add tests!

    return (file_name and (
        file_name in ('Packages.gz', 'Release', 'Sources.gz',)
        or file_name.endswith(('.deb', '.dsc',))
        or (file_name.startswith('Contents-') and file_name.endswith('.gz'))
    ))


def is_debian_url(uri):
    return 'debian.org' in uri


def is_ubuntu_url(uri):
    return 'ubuntu' in uri


@visit_router.route(
    'http://ftp.debian.org/.*/ls\-lR\.gz',
    'http://.*/ubuntu/ls\-lR\.gz',
    # mirrors
    'http://ftp.[a-z][a-z].debian.org/.*/ls\-lR\.gz',
)
class DebianDirectoryIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect package URIs from Debian-like repos with an ls-LR directory listing.
    """

    def get_uris(self, content):
        with gzip.open(content, 'rt') as f:
            content = f.read()

        url_template = self.uri.replace('ls-lR.gz', '{path}')

        for entry in ls.parse_directory_listing(content):
            if entry.type != ls.FILE:
                continue

            path = entry.path.lstrip('/')
            file_name = fileutils.file_name(path)

            if not is_collectible(file_name):
                continue

            if is_debian_url(self.uri):
                namespace = 'debian'
            elif is_ubuntu_url(self.uri):
                namespace = 'ubuntu'
            else:
                logger.error('Unknown Debian URI namespace: {}'.format(self.uri))
                continue

            if file_name.endswith(('.deb', '.udeb', '.tar.gz', '.tar.xz', '.tar.bz2', '.tar.lzma')):
                name, version, arch = debian_inspector.package.get_nva(file_name)
                package_url = PackageURL(
                    type='deb',
                    namespace=namespace,
                    name=name,
                    version=str(version),
                    qualifiers=dict(arch=arch) if arch else None).to_string()
            else:
                package_url = None

            yield URI(
                uri=url_template.format(path=path),
                package_url=None or package_url,
                file_name=file_name,
                date=entry.date,
                size=entry.size,
                source_uri=self.uri)


def parse_release(location):
    """
    Return a dictionary of data message from the debian Release file at `location`.

    A Release file contains return value like these:
        Origin: Debian
        Label: Debian
        Suite: stable
        Version: 8.3
        Codename: jessie
        Date: Sat, 23 Jan 2016 13:17:38 UTC
        Architectures: amd64 arm64 armel armhf i386 mips mipsel powerpc ppc64el s390x
        Components: main contrib non-free
        Description: Debian 8.3 Released 23 January 2016
        MD5Sum:
         f08bebee4d8727f4320c0ed6984a01c9  1194884 contrib/Contents-amd64
         c7f0b9213c9031cf89343a1bb8dbca3a    88565 contrib/Contents-amd64.gz
         36d2e8055b0cc185c8c5b081b414f4ce  1021655 contrib/Contents-arm64
         20bb294fefef1ab19e20ff0de7976ee2    72539 contrib/Contents-arm64.gz
         d2e1f415e05f53742b7133dd10ccf3af  1035687 contrib/Contents-armel
         5f24794a69552fbb10f303e33d35d380    73710 contrib/Contents-armel.gz
         d70a5e2db762a9eb493607e16f8c423e  1028590 contrib/Contents-armhf

    The MD5Sum key will return a list instead of a string value, element in the
    list is a dictionary keyed by:

            md5sum
            size
            name
    """
    return debcon.get_paragraphs_data_from_file(location)


def parse_copyright_only(location):
    """
    Return a DebianCopyright from the Debian copyright file at `location`.
    """
    return debcopy.DebianCopyright.from_file(location)


def parse_copyright_allinfo(location):
    """
    Return a DebianCopyright from the Debian copyright file at `location`.
    """
    return debcopy.DebianCopyright.from_file(location)


def parse_license(location):
    """
    Return a list of License paragraphs from Debian copyright file at location.
    """
    copyparas = debcopy.DebianCopyright.from_file(location)
    return [para for para in copyparas.paragraphs
            if isinstance(para, debian_inspector.copyright.CopyrightLicenseParagraph)]


def collect_source_packages(location):
    """
    Yield one Paragraph object per package from a plain text 'Sources' file at
    location.

    The source info is a dictionary, the content is like this:
        'Package': 'album'
        'Binary': 'album'
        'Version': '4.12-3'
        'Build-Depends': 'debhelper (>= 9)'
        'Architecture': 'all'
        'Format': '3.0 (quilt)'
    """
    return debcon.get_paragraphs_data_from_file(location)


def parse_packages_index(location):
    """
    Yield one Paragraph object per package from a plain text 'Packages' file at
    location.

    A typical Debian Packages file looks like this:
        http://ftp.debian.org/debian/dists/unstable/main/binary-mips/Packages.gz
    """
    return debcon.get_paragraphs_data_from_file(location)


@visit_router.route('http://ftp.debian.org/debian/dists/.*/Sources.gz')
class DebianSourcesVisitor(NonPersistentHttpVisitor):
    """
    Collect package URIs from a Sources gz data file.
    """

    def get_uris(self, content):
        base_url = 'http://ftp.debian.org/debian'
        with gzip.open(content, 'rb') as f:
            text = f.read()
        for source in debcon.get_paragraphs_data(text):
            dir_info = source.get('Directory')
            if not dir_info:
                continue
            package = source.get('Package')
            version = source.get('Version')

            package_url = None
            if package and version:
                package_url = PackageURL(
                    type='deb', namespace='debian', name=package,
                    version=version).to_string()

            dir_info = dir_info.lstrip('/')
            dir_url = base_url + '/{}'.format(dir_info)
            yield URI(uri=dir_url, package_url=package_url, source_uri=self.uri)


# TODO add .xz support
@visit_router.route('http://ftp.debian.org/debian/dists/.*Packages.gz')
class DebianPackagesVisitor(NonPersistentHttpVisitor):
    """
    Collect URIs  to actual .deb Packages and the content itself from a Packages gz data file.
    """

    def get_uris(self, content):
        base_url = 'http://ftp.debian.org/debian'
        with gzip.open(content, 'rb') as f:
            text = f.read()

        for package in debcon.get_paragraphs_data(text):
            file_info = package.get('Filename')
            if not file_info:
                continue

            package = package.get('Package')
            version = package.get('Version')

            if package and version:
                package_url = PackageURL(
                    type='deb',
                    namespace='debian',
                    name=package,
                    version=version).to_string()
            else:
                package_url = None

            # FIXME: we we do not keep the actual content... we should!
            file_info = file_info.lstrip('/')
            dir_url = base_url + file_info
            yield URI(
                uri=dir_url,
                package_url=package_url,
                source_uri=self.uri)


@visit_router.route('http://ftp.debian.org/debian/pool/.*\.dsc')
class DebianDescriptionVisitor(HttpVisitor):
    """
    Collect package data from a .dsc Package description file.
    There is no URI we can get from description file directly.
    """

    def dumps(self, content):
        dsc = debcon.Debian822.from_string(content)
        # FIXME: this does not make sense as this is a mapping-time thing
        return json.dumps(dsc.to_dict())


@visit_router.route('http://ftp.debian.org/debian/.*/Release')
class DebianReleaseVisitor(HttpVisitor):
    """
    Collect Release file content from a Release data file.
    """
    pass


@priority_router.route('pkg:deb/.*')
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a maven Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from debian and
    using it to create a new PackageDB entry. The binary package is then added to the
    scan queue afterwards. We also get the Package information for the
    accompanying source package and add it to the PackageDB and scan queue, if
    available.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    source_purl = kwargs.get("source_purl", None)
    try:
        package_url = PackageURL.from_string(purl_str)
        source_package_url = PackageURL.from_string(source_purl)

    except ValueError as e:
        error = f'error occured when parsing purl: {purl_str} source_purl: {source_purl} : {e}'
        return error

    has_version = bool(package_url.version)
    if has_version:
        error = map_debian_metadata_binary_and_source(
            package_url=package_url, 
            source_package_url=source_package_url,
        )

    return error


def map_debian_package(debian_package, package_content):
    """
    Add a debian `package_url` to the PackageDB.

    Return an error string if errors have occured in the process.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    db_package = None
    error = ''

    purl = debian_package.package_url
    if package_content == PackageContentType.BINARY:  
        download_url = debian_package.binary_archive_url
    elif package_content == PackageContentType.SOURCE_ARCHIVE:
        download_url = debian_package.source_archive_url
    
    response = requests.get(download_url)
    if not response.ok:
        msg = f'Package metadata not exist on debian: {download_url}'
        error += msg + '\n'
        logger.error(msg)
        return db_package, error

    purl_package = PackageData(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=purl.version,
        qualifiers=purl.qualifiers,
    )

    package, error_metadata = get_debian_package_metadata(debian_package)
    if error_metadata:
        error += error_metadata
    package.update_purl_fields(package_data=purl_package, replace=True)

    # This will be used to download and scan the package
    package.download_url = download_url

    # Set package_content value
    package.extra_data['package_content'] = package_content

    # If sha1 exists for an archive, we know we can create the package
    # Use purl info as base and create packages for binary and source package
    sha1 = get_package_sha1(package=package, field="download_url")
    if sha1:
        package.sha1 = sha1
        db_package, _, _, _ = merge_or_create_package(package, visit_level=50)
    else:
        msg = f'Failed to retrieve package archive: {purl.to_string()} from url: {download_url}'
        error += msg + '\n'
        logger.error(msg)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package)

    return db_package, error


def get_debian_package_metadata(debian_package):
    """
    """
    error = ''

    metadata_url = debian_package.package_metadata_url
    response = requests.get(metadata_url)
    if not response.ok:
        msg = f'Package metadata not exist on debian: {metadata_url}'
        error += msg + '\n'
        logger.error(msg)
        return None, error

    metadata_content = response.text
    filename = metadata_url.split("/")[-1]
    file_name, _, extension = filename.rpartition(".")
    temp_metadata_file = get_temp_file(file_name=file_name, extension=extension)
    with open(temp_metadata_file, 'a') as metadata_file:
        metadata_file.write(metadata_content)

    packages = DebianDscFileHandler.parse(location=temp_metadata_file)
    package = list(packages).pop()
    # In the case of looking up a maven package with qualifiers of
    # `classifiers=sources`, the purl of the package created from the pom does
    # not have the qualifiers, so we need to set them. Additionally, the download
    # url is not properly generated since it would be missing the sources bit
    # from the filename.
    package.qualifiers = debian_package.package_url.qualifiers

    return package, error


def map_debian_metadata_binary_and_source(package_url, source_package_url):
    """
    Get metadata for the binary and source release of the Debain package
    `package_url` and save it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ''

    if "repository_url" in package_url.qualifiers:
        base_url = package_url.qualifiers["repository_url"]
    else:
        base_url = DEBIAN_BASE_URL
    
    if "api_data_url" in package_url.qualifiers:
        metadata_base_url = package_url.qualifiers["api_data_url"]
    else:
        metadata_base_url = DEBIAN_METADATA_URL

    debian_package = DebianPackage(
        package_url=package_url,
        source_package_url=source_package_url,
        archive_base_url=base_url,
        metadata_base_url=metadata_base_url,
    )

    binary_package, emsg = map_debian_package(
        debian_package,
        PackageContentType.BINARY,
    )
    if emsg:
        error += emsg

    package_url.qualifiers['classifier'] = 'sources'
    source_package, emsg = map_debian_package(
        debian_package,
        PackageContentType.SOURCE_ARCHIVE,
    )
    if emsg:
        error += emsg

    if binary_package and source_package:
        make_relationship(
            from_package=binary_package,
            to_package=source_package,
            relationship=PackageRelation.Relationship.SOURCE_PACKAGE,
        )

    return error


@attr.s
class DebianPackage:

    archive_base_url = attr.ib(type=str)
    metadata_base_url = attr.ib(type=str)
    package_url = attr.ib(type=str)
    source_package_url = attr.ib(type=str)
    metadata_directory_url = attr.ib(type=str, default=None)
    archive_directory_url = attr.ib(type=str, default=None)

    def __attrs_post_init__(self, *args, **kwargs):
        self.set_debian_archive_directory()

    @property
    def package_archive_version(self):
        """
        """
        debvers = DebVersion.from_string(self.package_url.version)
        if debvers.revision != "0":
            purl_version = f"{debvers.upstream}-{debvers.revision}"
        else:
            purl_version = debvers.upstream
        return purl_version

    @property
    def binary_archive_url(self):
        """
        """
        purl_version = self.package_archive_version
        arch = self.package_url.qualifiers.get("architecture")
        if arch:
            archive_name =f"{self.package_url.name}_{purl_version}_{arch}.deb"
        else:
            archive_name =f"{self.package_url.name}_{purl_version}.deb"
        binary_package_url = self.archive_directory_url + f"{archive_name}"
        return binary_package_url

    @property
    def source_archive_url(self):
        """
        """
        debian_source_archive_formats = [
            ".tar.xz", ".tar.gz", ".orig.tar.xz", ".orig.tar.gz", ".orig.tar.bz2"
        ]

        source_version = self.package_archive_version
        if not self.source_package_url:
            source_package_name = self.package_url.name
        else:
            source_package_name = self.source_package_url.name
            if self.source_package_url.version:
                source_version = self.source_package_url.version

        for archive_format in debian_source_archive_formats:
            if ".orig" in archive_format:
                base_version_source = source_version.split('-')[0]
                archive_name = f"{source_package_name}_{base_version_source}" + archive_format
            else:
                archive_name = f"{source_package_name}_{source_version}" + archive_format
            source_package_url = self.archive_directory_url + archive_name
            response = requests.get(source_package_url)
            if response.ok:
                break

        return source_package_url

    @property
    def package_metadata_url(self):
        metadata_version = self.package_archive_version
        if not self.source_package_url:
            metadata_package_name = self.package_url.name
        else:
            metadata_package_name = self.source_package_url.name
            if self.source_package_url.version:
                metadata_version = self.source_package_url.version

        base_version_metadata = metadata_version.split('+')[0]
        metadata_dsc_package_url = self.archive_directory_url + f"{metadata_package_name}_{base_version_metadata}.dsc"
        response = requests.get(metadata_dsc_package_url)
        if not response.ok:
            metadata_dsc_package_url = self.archive_directory_url + f"{metadata_package_name}_{metadata_version}.dsc"

        return metadata_dsc_package_url

    def set_debian_archive_directory(self):
        """
        """
        base_url = self.archive_base_url
        index_folder = None
        if self.package_url.name.startswith('lib'):
            name_wout_lib = self.package_url.name.replace("lib", "")
            index_folder = 'lib' + name_wout_lib[0]
        else:
            index_folder = self.package_url.name[0]

        msg = "No directory exists for package at: "

        package_directory = f"{base_url}{index_folder}/{self.package_url.name}/"
        response = requests.get(package_directory)
        if not response.ok:
            if not self.source_package_url:
                raise PackageDirectoryMissingException(msg + str(package_directory))
            if self.source_package_url.name.startswith('lib'):
                name_wout_lib = self.source_package_url.name.replace("lib", "")
                index_folder = 'lib' + name_wout_lib[0]
            else:
                index_folder = self.source_package_url.name[0]
            package_directory = f"{base_url}{index_folder}/{self.source_package_url.name}/"
            response = requests.get(package_directory)
            if not response.ok:
                raise PackageDirectoryMissingException(msg + str(package_directory))

        self.archive_directory_url = package_directory


class PackageDirectoryMissingException(Exception):
    pass
