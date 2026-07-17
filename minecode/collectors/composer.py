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
from minecode.miners.composer import build_packages

from minecode import priority_router
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_composer_package_json(name):
    """
    Return the contents of the JSON file of the package from Packagist.
    Example: https://repo.packagist.org/p2/laravel/laravel.json
    """
    url = f"https://repo.packagist.org/p2/{name}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_composer_package(package_url, pipelines, priority=0):
    """
    Add a composer `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    namespace = package_url.namespace
    name = package_url.name

    package_name = f"{namespace}/{name}" if namespace else name

    package_json = get_composer_package_json(name=package_name)

    if not package_json:
        error = f"Package does not exist on packagist.org: {package_url}"
        logger.error(error)
        return error

    packages = build_packages(package_json, package_url)

    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:composer/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a composer Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    error_msg = map_composer_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
