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

from packagedcode.models import PackageData

from minecode import priority_router
from packagedb.models import PackageContentType


"""
Collect generic packages from a download URL.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_generic_package(package_url):
    """
    Add a npm `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    download_url = package_url.qualifiers.get('download_url')
    package = PackageData(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
        qualifiers=package_url.qualifiers,
        subpath=package_url.subpath,
        download_url=download_url,
    )
    # TODO: set package_content type

    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package)

    return error


@priority_router.route('pkg:generic/.*')
def process_request(purl_str):
    """
    Process `priority_resource_uri` containing a generic Package URL (PURL) with
    download_url as a qualifier
    """
    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f'error occured when parsing {purl_str}: {e}'
        return error

    download_url = package_url.qualifiers.get('download_url')
    if not download_url:
        error = f'package_url {purl_str} does not contain a download_url qualifier'
        return

    error_msg = map_generic_package(package_url)

    if error_msg:
        return error_msg
