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
from packageurl import PackageURL

from minecode.miners.pub import build_packages
from minecode import priority_router
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_pub_package_json(name, version=None):
    """
    Return the metadata JSON for a package from pub.dev API.
    Example: https://pub.dev/api/packages/flutter
    """
    if not version:
        url = f"https://pub.dev/api/packages/{name}"
    else:
        url = f"https://pub.dev/api/packages/{name}/versions/{version}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_pub_package(package_url, pipelines, priority=0):
    """
    Add a pub `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    name = package_url.name
    package_json = get_pub_package_json(name=name, version=package_url.version)

    if not package_json:
        error = f"Package does not exist on pub.dev: {package_url}"
        logger.error(error)
        return error

    packages = build_packages(package_json, package_url)
    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break
        print(db_package)
        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:pub/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a pub Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    error_msg = map_pub_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
