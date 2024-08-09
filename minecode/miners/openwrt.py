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
import os
import logging

from bs4 import BeautifulSoup
from debian_inspector import debcon
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import debutils
from minecode import seed
from minecode import map_router
from minecode import visit_router
from minecode.utils import extract_file
from minecode.collectors.debian import get_dependencies
from minecode.miners import Mapper
from minecode.miners import HttpVisitor
from minecode.miners import NonPersistentHttpVisitor
from minecode.miners import URI


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class OpenWrtSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://downloads.openwrt.org/chaos_calmer/15.05/'


@visit_router.route('https://downloads.openwrt.org/.*/')
class OpenWrtDownloadPagesVisitor(HttpVisitor):
    """
    Visit the OpwnWRT download HTML page and return URIs parsed from HTML page.
    """
    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        for td in page.find_all(name='td'):
            a = td.find(name='a')
            if not a:
                continue
            href = a['href']
            if href == '../':  # Ignore the parent url
                continue

            # Add the uri for next loop if it ends with "/", which means it'a
            # folder resource uri
            if href.endswith('/'):
                package_url = PackageURL(type='openwrt', name=href.replace('/', '')).to_string()
                yield URI(uri=self.uri + href, package_url=package_url, source_uri=self.uri)
            elif href.endswith(('Packages', 'Packages.gz', '.ipk')):
                yield URI(uri=self.uri + href, source_uri=self.uri)


@visit_router.route('https://downloads.openwrt.org/.*/Packages\.gz')
class OpenWrtPackageIndexVisitor(NonPersistentHttpVisitor):
    """
    Visit the OpwnWRT Packages.gz Index file and collect uris.
    """
    def get_uris(self, content):
        with gzip.open(content, 'rb') as f:
            content = f.read()

        for package in debcon.get_paragraphs_data(content):
            file_info = package.get('Filename')
            if not file_info:
                continue
            version = package.get('Version')
            md5sum = package.get('MD5Sum')
            sha256sum = package.get('SHA256sum')
            package_name = package.get('Package')
            package_url = None
            if package_name and version:
                package_url = PackageURL(type='openwrt', name=package_name, version=version).to_string()
            file_info = file_info.lstrip('/')
            dir_url = self.uri.replace('Packages.gz', '') + file_info
            yield URI(uri=dir_url, package_url=package_url, data=json.dumps(str(package)), source_uri=self.uri, md5=md5sum, sha256=sha256sum,)


@visit_router.route('https://downloads.openwrt.org/.*\.ipk')
class OpenWrtIpkPackageArchiveVisitor(NonPersistentHttpVisitor):
    """
    Visit the OpwnWRT Packages.gz and collect uris.
    """
    def dumps(self, content):
        """
        Extract an ipk package archive and its control.targ.gz. Parse the
        control file and return a JSON string from these data.
        """
        extracted_location = extract_file(content)
        control_targz = os.path.join(extracted_location, 'control.tar.gz')
        control_extracted_folder = extract_file(control_targz)
        control_location = os.path.join(control_extracted_folder, 'control')
        parsed = debcon.Debian822.from_file(control_location)
        return json.dumps(parsed)


@map_router.route('https://downloads.openwrt.org/.*\.ipk')
class OpenwrtIpkMetadataMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackage built from resource_uri record for a single package
        version. Yield as many Package as there are download URLs.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages(metadata, resource_uri.package_url, uri)


def build_packages(metadata, purl=None, uri=None):
    """
    Yield ScannedPackage built from the passing metadata.
    metadata: metadata mapping
    purl: String value of the package url of the ResourceURI object
    """
    common_data = dict(
        type='openwrt',
        datasource_id='openwrt_metadata',
        name=metadata.get('Package'),
        version=metadata.get('Version'),
        description=metadata.get('Description'),
        size=metadata.get('Installed-Size'),
    )

    dependencies = get_dependencies(metadata, ['Depends'])
    if dependencies:
        common_data['dependencies'] = dependencies

    maintainers = metadata.get('Maintainer')
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            parties = common_data.get('parties')
            if not parties:
                common_data['parties'] = []
            party = scan_models.Party(name=name, role='maintainer', email=email)
            common_data['parties'].append(party)

    lic = metadata.get('License')
    if lic:
        common_data['declared_license'] = lic

    common_data['keywords'] = []
    section = metadata.get('Section')
    if section:
        common_data['keywords'].append(section)
    architecture = metadata.get('Architecture')
    if architecture:
        common_data['keywords'].append(architecture)
    package = scan_models.Package.from_package_data(
        package_data=common_data,
        datafile_path=uri,
    )
    package.set_purl(purl)
    yield package
