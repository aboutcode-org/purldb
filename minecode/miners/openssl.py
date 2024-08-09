#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from bs4 import BeautifulSoup
from datetime import datetime
import logging

from commoncode import fileutils
from packageurl import PackageURL
from packagedcode import models as scan_models

from minecode import map_router
from minecode.miners import Mapper
from minecode.utils import parse_date
from minecode import priority_router
from minecode import seed
from minecode import visit_router
from minecode.utils import is_int
from minecode.miners import HttpVisitor
from minecode.miners import URI
from minecode.miners.generic import map_fetchcode_supported_package


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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


# Indexing OpenSSL PURLs requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route('pkg:openssl/openssl@.*')
def process_request_dir_listed(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a OpenSSL Package URL (PURL)
    supported by fetchcode.

    This involves obtaining Package information for the PURL using
    https://github.com/aboutcode-org/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get('addon_pipelines', [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get('priority', 0)

    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error

    error_msg = map_fetchcode_supported_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg


@map_router.route('https://ftp.openssl.org/.*')
class OpenSSLMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackage built from resource_uri record for a single package
        version. Yield as many Package from the uri
        """
        return build_packages(resource_uri, resource_uri.package_url)


def build_packages(resource_uri, purl=None):
    """
    Yield  Package from resource_uri metadata
    resource_uri: ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    uri = resource_uri.uri
    file_name = fileutils.file_name(uri)
    version = file_name.replace('.tar.gz', '').replace('openssl-', '').replace('.tar.gz', '').replace(
        '.asc', '').replace('.md5', '').replace('.sha1', '').replace('.sha256', '')
    common_data = dict(
        datasource_id="openssl_metadeta",
        type='generic',
        name=file_name,
        description='The OpenSSL Project is a collaborative effort to develop a robust, commercial-grade, fully featured, and Open Source toolkit implementing the Transport Layer Security (TLS) protocols (including SSLv3) as well as a full-strength general purpose cryptographic library.',
        version=version,
        size=resource_uri.size,
        release_date=parse_date(resource_uri.last_modified_date),
        extracted_license_statement='OpenSSL License',
        license_detections=[],
        homepage_url='https://www.openssl.org/',
        download_url=uri,
        copyright='Copyright (c) 1998-2018 The OpenSSL Project\nCopyright (c) 1995-1998 Eric A. Young, Tim J. Hudson\nAll rights reserved.',
        vcs_url='git+https://github.com/openssl/openssl.git',
        code_view_url='https://github.com/openssl/openssl',
        bug_tracking_url='https://github.com/openssl/openssl/issues',
    )
    package = scan_models.Package.from_package_data(
        package_data=common_data,
        datafile_path=uri,
    )
    package.set_purl(purl)
    yield package
