#
# Copyright (c) 2017 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import gzip
import json
import os

from bs4 import BeautifulSoup
from debian_inspector import debcon
from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.utils import extract_file
from minecode.visitors import HttpVisitor
from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import URI


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
