#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import gzip
import json
import logging

from commoncode import fileutils
import debian_inspector
from debian_inspector import debcon
from debian_inspector import copyright as debcopy
from packageurl import PackageURL

from discovery import ls
from discovery import seed
from discovery import visit_router
from discovery.visitors import HttpVisitor
from discovery.visitors import NonPersistentHttpVisitor
from discovery.visitors import URI


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
# DEBIAN_BASE_URL = 'http://ftp.debian.org/debian/'
# Other URLs and sources to consider
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
        with gzip.open(content, 'rb') as f:
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

            name, version, arch = debian_inspector.package.get_nva(file_name)
            package_url = PackageURL(
                type='deb',
                namespace=namespace,
                name=name,
                version=version,
                qualifiers=dict(arch=arch) if arch else None)

            yield URI(
                uri=url_template.format(path=path),
                package_url=package_url.to_string(),
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
        dsc = debcon. Debian822.from_string(content)
        # FIXME: this does not make sense as this is a mapping-time thing
        return json.dumps(dsc.to_dict())


@visit_router.route('http://ftp.debian.org/debian/.*/Release')
class DebianReleaseVisitor(HttpVisitor):
    """
    Collect Release file content from a Release data file.
    """
    pass
