#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from bs4 import BeautifulSoup
from datetime import datetime

from commoncode import fileutils
from packageurl import PackageURL

from minecode import priority_router
from minecode import seed
from minecode import visit_router
from minecode.utils import is_int
from minecode.visitors import HttpVisitor
from minecode.visitors import URI
from minecode.visitors.generic import map_fetchcode_supported_package


class OpenSSLSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://ftp.openssl.org/'


@visit_router.route('https://ftp.openssl.org/',
                    'https://ftp.openssl.org/.*/')
class OpenSSLVisitor(HttpVisitor):
    """
    Collect package metadata URIs from the open SSL HTML site.
    """

    def get_uris(self, content):
        """
        Return URIs objects and the corresponding size, file date info.
        """
        page = BeautifulSoup(content, 'lxml')
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue
            href = a['href']
            if not href:
                continue
            if href.startswith('?') or href.startswith('/'):
                # if href is not valid resource, ignore, for example, it's a
                # link to parent link etc.
                continue
            url = self.uri + href
            next_sibling = a.parent.findNext('td')

            date = None
            if next_sibling and next_sibling.contents:
                date = next_sibling.contents[0].strip()
                # The passing date format is like: 2014-11-19 17:48
                date = datetime.strptime(date, '%Y-%m-%d %H:%M')

            if next_sibling:
                next_next = next_sibling.findNext('td')
                if next_next and next_next.contents:
                    size = next_next.contents[0].strip()
                    if size and is_int(size):
                        # By default, if the unit is not shown, it means k.
                        size = str(int(size) * 1024)
                    if size.endswith(('M', 'm')):
                        # If the size is mega byte, and the format is a float
                        # instead of int, since it's possible like 5.1M
                        size = str(
                            int(float(size.replace('M', '').replace('m', '')) * 1024 * 1024))
                    elif size.endswith('G') or size.endswith('G'):
                        # if the size is gega byte
                        size = str(
                            int(float(size.replace('G', '').replace('g', '')) * 1024 * 1024 * 1024))
                    if size == '-':
                        # if it's folder, ignore the size
                        size = None
            file_name = None
            if not url.endswith('/'):
                file_name = fileutils.file_name(url)
            if file_name:
                # If it's a file, pass the url to mapper by setting the visited
                # to True
                package_url = None
                version = None
                if 'tar.gz' in file_name:
                    version = file_name.replace('openssl-', '').partition('.tar.gz')[0]
                package_url = PackageURL(type='generic', name='openssl', version=version).to_string()
                yield URI(uri=url, source_uri=self.uri, package_url=package_url, date=date, file_name=file_name, size=size)
            else:
                yield URI(uri=url, source_uri=self.uri, date=date, size=size)


@priority_router.route('pkg:openssl/openssl@.*')
def process_request_dir_listed(purl_str):
    """
    Process `priority_resource_uri` containing a OpenSSL Package URL (PURL)
    supported by fetchcode.

    This involves obtaining Package information for the PURL using
    https://github.com/nexB/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error

    error_msg = map_fetchcode_supported_package(package_url)

    if error_msg:
        return error_msg