#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import defaultdict
import attr
import gzip
import json
import logging

from commoncode import fileutils
import debian_inspector
from debian_inspector import debcon
from debian_inspector import copyright as debcopy
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import debutils
from minecode import ls
from minecode import seed
from minecode import map_router
from minecode import visit_router
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.miners import NonPersistentHttpVisitor
from minecode.miners import URI
from minecode.utils import form_vcs_url


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

UBUNTU_BASE_URL = "http://archive.ubuntu.com/ubuntu/pool/main/"
UBUNTU_METADATA_URL = "http://changelogs.ubuntu.com/changelogs/pool/main/"

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
                logger.error(
                    'Unknown Debian URI namespace: {}'.format(self.uri))
                continue

            if file_name.endswith(('.deb', '.udeb', '.tar.gz', '.tar.xz', '.tar.bz2', '.tar.lzma')):
                name, version, arch = debian_inspector.package.get_nva(
                    file_name)
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


@map_router.route('http://ftp.debian.org/debian/pool/.*\.dsc')
class DebianDescriptionMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield packages parsed from a dsc Debian control file mapping.
        """
        return parse_description(
            metadata=json.loads(resource_uri.data),
            purl=resource_uri.package_url,
            base_download_url=None)


def get_files(text):
    """
    Yield tuples of (checksum, size, filename) collected from a files field
    `text`.
    """
    if text:
        for line in text.splitlines(False):
            # we have htree space-separated items, so we perform two partitions
            line = ' '.join(line.split())
            checksum, _, rest = line.partition(' ')
            size, _, filename = rest.partition(' ')
            yield checksum, size, filename


def parse_description(metadata, purl=None, base_download_url=None):
    """
    Yield Scanned Package parse from description `metadata` mapping
    for a single package version.
    Yield as many Package as there are download URLs.
    Optionally use the `purl` Package URL string if provided.
    """
    # FIXME: this may not be correct: Source and Binary are package names
    common_data = dict(
        name=metadata['Source'],
        version=metadata['Version'],
        homepage_url=metadata.get('Homepage'),
        code_view_url=metadata.get('Vcs-Browser'),
        parties=[]
    )

    if metadata.get('Label'):
        common_data['keywords'] = [metadata.get('Label')]

    vcs_tool, vcs_repo = get_vcs_repo(metadata)
    if vcs_tool and vcs_repo:
        vcs_repo = form_vcs_url(vcs_tool, vcs_repo)
    common_data['vcs_url'] = vcs_repo

    dependencies = get_dependencies(metadata)
    if dependencies:
        common_data['dependencies'] = dependencies

    # TODO: add "original maintainer" seen in Ubuntu
    maintainer = metadata.get('Maintainer')
    if maintainer:
        name, email = debutils.parse_email(maintainer)
        if name:
            party = scan_models.Party(
                name=name, role='maintainer', email=email)
            common_data['parties'].append(party)

    @attr.s()
    class File(object):
        name = attr.ib(default=None)
        size = attr.ib(default=None)
        md5 = attr.ib(default=None)
        sha1 = attr.ib(default=None)
        sha256 = attr.ib(default=None)

    def collect_files(existing_files, field_value, checksum_name):
        for checksum, size, name in get_files(field_value):
            fl = existing_files[name]
            if not fl.name:
                fl.name = name
                fl.size = size
            setattr(fl, checksum_name, checksum)

    # TODO: what do we do with files?
    # FIXME: we should store them in the package record
    files = defaultdict(File)
    collect_files(existing_files=files, field_value=metadata.get('Files'), checksum_name='md5')
    collect_files(existing_files=files, field_value=metadata.get('Checksums-Sha1'), checksum_name='sha1')
    collect_files(existing_files=files, field_value=metadata.get('Checksums-Sha256'), checksum_name='sha256')

    # FIXME: craft a download_url
    download_url = None
    if base_download_url:
        download_url = None
        common_data['download_url'] = download_url

    package = scan_models.DebianPackage(**common_data)
    package.set_purl(purl)
    yield package


@map_router.route('http://ftp.debian.org/debian/dists/.*Sources.gz')
class DebianSourceFileMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackages built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        return parse_packages(metadata, resource_uri.package_url)


def build_source_file_packages(metadata, purl=None):
    """
    Yield packages from the passing source file metadata.
    metadata: json metadata content
    purl: String value of the package url of the ResourceURI object
    """
    for source in debcon.get_paragraphs_data(metadata):
        package_name = source.get('Package')

        parties = []
        maintainer_names = debutils.comma_separated(source.get('Maintainer', ''))
        if maintainer_names:
            for maintainer in maintainer_names:
                name, email = debutils.parse_email(maintainer)
                if name:
                    party = scan_models.Party(
                        name=name, role='maintainer', email=email)
                    parties.append(party)
        contributor_names = debutils.comma_separated(source.get('Uploaders', ''))
        if contributor_names:
            for contributor in contributor_names:
                name, email = debutils.parse_email(contributor)
                if name:
                    party = scan_models.Party(
                        name=name, role='contributor', email=email)
                    parties.append(party)

        dependencies = get_dependencies(source, ['Build-Depends'])

        keywords = set()
        keywords.update(debutils.comma_separated(source.get('Binary', '')))
        if source.get('Section'):
            keywords.add(source.get('Section'))

        files = source.get('Files')
        for f in files:
            name = f.get('name')
            package = dict(
                name=package_name,
                version=source.get('Version'),
                dependencies=dependencies,
                parties=parties,
                code_view_url=source.get('Vcs-Browser'),
                homepage_url=source.get('Homepage'),
                keywords=list(keywords),
            )

            download_url = 'http://ftp.debian.org/debian/{path}/{name}'.format(
                path=source.get('Directory'),
                name=name)

            package['download_url'] = download_url

            vcs_tool, vcs_repo = get_vcs_repo(source)
            if vcs_tool and vcs_repo:
                vcs_repo = form_vcs_url(vcs_tool, vcs_repo)
            package['vcs_url'] = vcs_repo

            package['md5'] = f.get('md5sum')
            # TODO: Why would we have more than a single SHA1 or SHA256
            sha1s = source.get('Checksums-Sha1', [])
            for sha1 in sha1s:
                sha1value = sha1.get('sha1')
                name = sha1.get('name')
                if name and sha1value:
                    package['sha1'] = sha1value
            sha256s = source.get('Checksums-Sha256', [])
            for sha256 in sha256s:
                sha256value = sha256.get('sha256')
                name = sha256.get('name')
                if name and sha256value:
                    package['sha256'] = sha256value
            package = scan_models.DebianPackage(**package)
            package.set_purl(purl)
            yield package


@map_router.route('http://ftp.debian.org/debian/dists/.*Packages.gz')
class DebianPackageFileMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages from a Debian Packages inex.
        """
        metadata = resource_uri.data
        return parse_packages(metadata, resource_uri.package_url)


def get_programming_language(tags):
    """
    Return the programming language extracted from list of `tags` strings.
    """
    for tag in tags:
        key, _, value = tag.partition('::')
        if key == 'implemented-in':
            return value


def parse_packages(metadata, purl=None):
    """
    Yield packages from Debian package text data.
    metadata: Debian data (e.g. a Packages files)
    purl: String value of the package url of the ResourceURI object
    """
    for pack in debcon.get_paragraphs_data(metadata):
        data = dict(
            name=pack['Package'],
            version=pack['Version'],
            homepage_url=pack.get('Homepage'),
            code_view_url=pack.get('Vcs-Browser'),
            description=pack.get('Description'),
            bug_tracking_url=pack.get('Bugs'),
            parties=[],
            md5=pack.get('MD5sum'),
            sha1=pack.get('SHA1'),
            sha256=pack.get('SHA256'),
        )

        filename = pack.get('Filename'),
        if filename:
            data['download_url'] = 'http://ftp.debian.org/debian/{}'.format(filename)

        maintainers = pack.get('Maintainer')
        if maintainers:
            name, email = debutils.parse_email(maintainers)
            if name:
                party = scan_models.Party(
                    name=name, role='maintainer', email=email)
                data['parties'].append(party)

        dependencies = get_dependencies(pack)
        if dependencies:
            data['dependencies'] = dependencies

        keywords = debutils.comma_separated(pack.get('Tag', ''))

        section = pack.get('Section')
        if section:
            keywords.append(section)
        data['keywords'] = keywords

        data['primary_language'] = get_programming_language(keywords)

        package = scan_models.DebianPackage(**data)
        if purl:
            package.set_purl(purl)
        yield package


#################################################################################
# FIXME: this cannot work since we do not fetch these yet AND what are the zip jar and gz in this???
#################################################################################


@map_router.route('http://ftp.debian.org/debian/dists/.*\.zip',
                  'http://ftp.debian.org/debian/dists/.*\.jar',
                  'http://ftp.debian.org/debian/dists/.*\.gz')
class DebianArchiveFileMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        return build_packages_from_dist_archive(resource_uri.data, resource_uri.uri)


def build_packages_from_dist_archive(metadata, uri):
    """
    Yield Package built from Debian project URI and the ls content associated
    which is a result by running ls LR command at the Debiain root folder.
    Yield as many Package as there are download URLs.
    """
    debian_dist_length = len('http://ftp.debian.org/debian/dists')
    # The parent folder URI related to uri file itself.
    folder_uri = uri[debian_dist_length: uri.rindex('/')]
    debian_dist_length = len('http://ftp.debian.org/debian/dists')
    # project name by trucking the uri
    name = uri[debian_dist_length:uri.index('/', debian_dist_length)]
    folder_length = debian_dist_length + len(name) + 1
    # version by analysing the uri
    version = uri[folder_length:uri.index('/', folder_length)]
    common_data = dict(
        datasource_id="debian_archive_file",
        name=name,
        version=version,
    )

    # FIXME: this is NOT RIGHT
    def get_resourceuri_by_uri(uri):
        """
        Return the Resource URI by searching with passing uri string value.
        """
        from minecode.models import ResourceURI
        uris = ResourceURI.objects.filter(uri=uri)
        if uris:
            return uris[0]

    url_template = 'http://ftp.debian.org/debian/dists{name}'
    download_urls = []
    for entry in ls.parse_directory_listing(metadata):
        if entry.type != ls.FILE:
            continue
        path = entry.path

        if path.startswith(folder_uri):
            path = path.lstrip('/')
            url = url_template.format(name=path)
            # FIXME: this is NOT RIGHT
            if path.endswith('.md5') and url.replace('.md5', '') == uri:
                if get_resourceuri_by_uri(url) and get_resourceuri_by_uri(url).md5:
                    common_data['md5'] = get_resourceuri_by_uri(url).md5
            # FIXME: this is NOT RIGHT
            if path.endswith('.sha') and url.replace('.sha', '') == uri:
                if get_resourceuri_by_uri(url) and get_resourceuri_by_uri(url).sha1:
                    common_data['sha1'] = get_resourceuri_by_uri(url).sha1

            if path.endswith(('.jar', 'zip', 'gz')) and url != uri:
                download_urls.append(url)

    if download_urls:
        for download_url in download_urls:
            package = scan_models.Package.from_package_data(
                package_data=common_data,
                datafile_path=uri,
            )
            package['download_url'] = download_url
            yield package
    else:
        # yield package without a download_url value
        package = scan_models.Package.from_package_data(
                package_data=common_data,
                datafile_path=uri,
            )
        # FIXME: this is NOT RIGHT: purl is not defined
        package.set_purl(package.purl)
        yield package
