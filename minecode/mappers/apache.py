#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import json
import logging

from packageurl import PackageURL

from commoncode import fileutils
import packagedcode.models as scan_models

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import parse_date
from minecode.visitors.apache import CHECKSUM_EXTS


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# TODO: Declared license should be an Apache license

# common licenses found in JSON
APACHE_LICENSE_URL = {
    'http://usefulinc.com/doap/licenses/asl20',
    'https://usefulinc.com/doap/licenses/asl20',
    'http://spdx.org/licenses/Apache-2.0',
    'https://spdx.org/licenses/Apache-2.0',
    'http://www.apache.org/licenses/LICENSE-2.0',
    'https://www.apache.org/licenses/LICENSE-2.0',
    'http://www.apache.org/licenses/LICENSE-2.0.txt',
    'https://www.apache.org/licenses/LICENSE-2.0.txt',
    'http://www.apache.org/licenses/',
    'http://forrest.apache.org/license.html',
    'https://svn.apache.org/repos/asf/tomee/tomee/trunk/LICENSE',
}


# FIXME: this is NOT specific to a download URL but to a project: disabled for now
# @map_router.route('https://projects.apache.org/json/foundation/projects.json')
class ApacheProjectJsonMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        metadata = json.loads(resource_uri.data, object_pairs_hook=OrderedDict)
        return build_packages_from_projects(metadata)


def build_packages_from_projects(metadata):
    """
    Yield Package built from Apache a `metadata` mapping
    which is a dictionary keyed by project name and values are project_metadata.
    Yield as many Package as there are download URLs.
    """
    for project_name, project_meta in metadata.items():
        short_desc = project_meta.get('shortdesc')
        long_desc = project_meta.get('description')
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = '\n'.join(descriptions)
        common_data = dict(
            type='apache',
            name=project_name,
            description=description,
            homepage_url=project_meta.get('homepage'),
            bug_tracking_url=project_meta.get('bug-database'),
            primary_language=project_meta.get('programming-language'),
        )

        # FIXME: setting the download-page as the download_url is not right
        if project_meta.get('download-page'):
            download_url = project_meta.get('download-page')
            common_data['download_url'] = download_url
        for repo in project_meta.get('repository', []):
            common_data['code_view_url'] = repo
            # Package code_view_url only support one URL, so break when
            # finding a code_view_url
            break

        maintainers = project_meta.get('maintainer', [])
        for maintainer in maintainers:
            mailbox = maintainer.get('mbox', '').replace('mailto:', '')
            name = maintainer.get('name')
            party = scan_models.Party(type=scan_models.party_person, name=name, role='maintainer', email=mailbox)
            parties = common_data.get('parties')
            if not parties:
                common_data['parties'] = []
            common_data['parties'].append(party)

        # license is just a URL in the json file, for example:
        # http://usefulinc.com/doap/licenses/asl20
        license_url = project_meta.get('license')
        common_data['declared_license'] = license_url

        if license_url in APACHE_LICENSE_URL:
            common_data['license_expression'] = 'apache-2.0'

        keywords = []
        category = project_meta.get('category', '')
        for kw in category.split(','):
            kw = kw.strip()
            if kw:
                keywords.append(kw)
        common_data['keywords'] = keywords

        common_data['primary_language'] = project_meta.get('programming-language')

        # FIXME: these cannot be related to actual packages with a download URL
        releases = project_meta.get('release')
        if releases:
            for release in releases:
                rdata = dict(common_data)
                rdata['version'] = release.get('revision')
                if release.get('created') and len(release.get('created')) == 10:
                    rdata['release_date'] = parse_date(release.get('created'))
                else:
                    logger.warn('Unexpected date format for release date: {}'.format(release.get('created')))
                package = scan_models.Package(**rdata)
                yield package
        else:
            package = scan_models.Package(**common_data)
            yield package


# FIXME: this is NOT specific to a download URL but to a project: disabled for now
# FIXME: this is casting too wide a net!
# @map_router.route('http?://[\w\-\.]+.incubator.apache.org/"')
class ApachePodlingsMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        metadata = json.loads(resource_uri.data, object_pairs_hook=OrderedDict)
        return build_packages_from_podlings(metadata, resource_uri.package_url)


def build_packages_from_podlings(metadata, purl):
    """
    Yield Package built from Apache podlings metadata
    which is a dictionary keyed by project name and values are project_metadata.
    Yield as many Package as there are download URLs.
    """
    name = metadata.get('name')
    if name:
        common_data = dict(
            type='apache-podling',
            name=name,
            description=metadata.get('description'),
            homepage_url=metadata.get('homepage'),
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package


@map_router.route('http?s://(archive\.)?apache\.org/dist/.*')
class ApacheDownloadMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages build from a bare download URI or download checksum URI.
        """
        if uri.endswith(CHECKSUM_EXTS):
            # 1. create a regular package from the URL stripped from its checksum extension
            archive_uri, _, checksum_type = uri.rpartition('.')

            pack = build_package_from_download(archive_uri, resource_uri.package_url)
            # 2. collect the checksum inside the file
            # and attach it to the package
            checksum_value = resource_uri.data.strip()
            if checksum_value:
                checksum_field_name = 'download_{checksum_type}'.format(**locals())
                setattr(pack, checksum_field_name, checksum_value)
                yield pack
        else:
            # a plain download URI
            yield build_package_from_download(uri, resource_uri.package_url)


def build_package_from_download(uri, purl=None):
    """
    Return a Package built from an Apache dist download archive URL.

    The uri could be:
    http://archive.apache.org/dist/groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip
    https://apache.org/dist/chemistry/opencmis/1.1.0/chemistry-opencmis-dist-1.1.0-server-webapps.zip
    """
    name, version = get_name_version(uri)
    if purl:
        purl = PackageURL.from_string(purl)
        if not name:
            name = purl.name
    # FIXME: use purl data??
    package = scan_models.Package(
        type='apache',
        namespace=purl.namespace,
        name=name,
        version=version,
        download_url=uri,
    )
    package.set_purl(purl)
    return package


# FIXME: there should be only one such method and this one is rather weak
def get_name_version(uri):
    """
    Return name and version extracted from a path.
    """
    # base_url will end being 'https://archive.apache.org/dist' or  'https://apache.org/dist'
    # path is the uri without base url, for example:
    # /groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip
    _, _, path = uri.partition('apache.org/dist/')
    base_name = fileutils.file_base_name(path)
    version = None
    package_name = ''
    name_segments = base_name.split('-')
    for segment in name_segments:
        try:
            # To test if each split segment with . is integer.
            # For example in '1.2.3' all chars are integer or period.
            # If so, this segment is a version segment.
            if version:
                # The segment after integer segment should belong to version too.
                # For example: turbine-4.0-M1, after detecting 4.0,
                # M1 should be including in version too, so the final version is 4.0-M1
                version = '-'.join([version, segment])
                continue

            is_all_int = all(n.isdigit() for n in segment.split('.'))
            if is_all_int:
                version = segment
        except ValueError:
            # Connect the package_name with - because we split it with - eariler, util
            # when we meet version, package_name should be good.
            if not package_name:
                package_name = segment
            else:
                package_name = ('-').join([package_name, segment])
            continue
    return package_name, version
