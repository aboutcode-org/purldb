#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from collections import defaultdict
import json
import logging

import attr
from debian_inspector import debcon
from packagedcode import models as scan_models
from packageurl import PackageURL

from discovery import ls
from discovery import map_router
from discovery.mappers import Mapper
from discovery.utils import form_vcs_url
# from discovery import debutils


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# FIXME: We are not returning download URLs. Returned information is incorrect


def get_dependencies(data):
    """
    Return a list of DependentPackage extracted from a Debian `data` mapping.
    """
    scopes = {
        'Build-Depends': dict(is_runtime=False, is_optional=True),
        'Depends': dict(is_runtime=True, is_optional=False),
        'Pre-Depends': dict(is_runtime=True, is_optional=False),
        # 'Provides': dict(is_runtime=True, is_optional=False),
        # 'Recommends': dict(is_runtime=True, is_optional=True),
        # 'Suggests': dict(is_runtime=True, is_optional=True),
    }
    dep_pkgs = []
    for scope, flags in scopes.items():
        depends = data.get(scope)
        if not depends:
            continue

        dependencies = None  # debutils.comma_separated(depends)
        if not dependencies:
            continue
        # break each dep in package names and version constraints
        # FIXME:!!!
        for name in dependencies:
            purl = PackageURL(type='deb', namespace='debian', name=name)
            dep = scan_models.DependentPackage(purl=purl.to_string(), score=scope, **flags)
            dep_pkgs.append(dep)

    return dep_pkgs


def get_vcs_repo(description):
    """
    Return a tuple of (vcs_tool, vcs_repo) or (None, None) if no vcs_repo is found.
    """
    repos = []
    for vcs_tool, vcs_repo in description.items():
        vcs_tool = vcs_tool.lower()
        if not vcs_tool.startswith('vcs-') or vcs_tool.startswith('vcs-browser'):
            continue
        _, _, vcs_tool = vcs_tool.partition('-')
        repos.append((vcs_tool, vcs_repo))

    if len(repos) > 1:
        raise TypeError('Debian description with more than one Vcs repos: %(repos)r' % locals())

    if repos:
        vcs_tool, vcs_repo = repos[0]
    else:
        vcs_tool = None
        vcs_repo = None

    return vcs_tool, vcs_repo


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
        name=name,
        version=version,
    )

    # FIXME: this is NOT RIGHT
    def get_resourceuri_by_uri(uri):
        """
        Return the Resource URI by searching with passing uri string value.
        """
        from discovery.models import ResourceURI
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
            package = scan_models.Package(**common_data)
            package['download_url'] = download_url
            yield package
    else:
        # yield package without a download_url value
        package = scan_models.DebianPackage(**common_data)
        # FIXME: this is NOT RIGHT: purl is not defined
        package.set_purl(purl)
        yield package
