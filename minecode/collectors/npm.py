#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging

import requests
from packagedcode.npm import NpmPackageJsonHandler
from packagedcode.npm import npm_api_url
from packageurl import PackageURL

from minecode import priority_router
from packagedb.models import PackageContentType

"""
Collect NPM packages from npm registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_package_json(namespace, name, version):
    """
    Return the contents of the package.json file of the package described by the purl
    field arguments in a string.
    """
    # Create URLs using purl fields
    url = npm_api_url(
        namespace=namespace,
        name=name,
        version=version,
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_npm_package(package_url, pipelines, priority=0):
    """
    Add a npm `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    package_json = get_package_json(
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
    )

    if not package_json:
        error = f"Package does not exist on npmjs: {package_url}"
        logger.error(error)
        return error

    package = NpmPackageJsonHandler._parse(json_data=package_json)
    package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE

    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(
            package=db_package, pipelines=pipelines, priority=priority
        )

    return error


@priority_router.route("pkg:npm/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a npm Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from npm and
    using it to create a new PackageDB entry. The package is then added to the
    scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    if not package_url.version:
        return

    error_msg = map_npm_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
