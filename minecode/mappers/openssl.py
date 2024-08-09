#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import datetime
import logging

from commoncode import fileutils
from packagedcode import models as scan_models

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import parse_date

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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
