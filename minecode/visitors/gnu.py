#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging

from packageurl import PackageURL

from minecode import priority_router
from minecode.visitors.generic import map_directory_listed_package

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@priority_router.route("pkg:gnu/.*")
def process_request(purl_str):
    """
    Process `priority_resource_uri` containing a GNU Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL using
    https://github.com/nexB/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    package_url = PackageURL.from_string(purl_str)
    if not package_url.version:
        return

    error_msg = map_directory_listed_package(package_url)

    if error_msg:
        return error_msg
