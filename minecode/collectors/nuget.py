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

from minecode import priority_router
from minecode.miners.nuget import build_packages_with_json
from packagedb.models import PackageContentType

"""
Collect Nuget packages from nuget registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_package_json(name):
    """
    Return the contents of the JSON file of the package.
    """
    # Create URLs using project name.
    url = f"https://api.nuget.org/v3/registration5-gz-semver2/{name}/index.json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_nuget_package(package_url, pipelines, priority=0):
    """
    Add a nuget `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    error = ""
    package_json = get_package_json(name=package_url.name.lower())

    if not package_json:
        error = f"Package does not exist on crates.io: {package_url}"
        logger.error(error)
        return error

    packages_metadata = package_json.get("items")[0].get("items")

    for package_metadata in packages_metadata:
        metadata = package_metadata["catalogEntry"]
        if package_url.version:
            if metadata.get("version") == package_url.version:
                built_package = build_packages_with_json(metadata, package_url)
            else:
                continue
        else:
            built_package = build_packages_with_json(metadata, package_url)

        for package in built_package:
            package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
            db_package, _, _, error = merge_or_create_package(package, visit_level=0)
            if error:
                break

            # Submit package for scanning
            if db_package:
                add_package_to_scan_queue(
                    package=db_package, pipelines=pipelines, priority=priority
                )

    return error


@priority_router.route("pkg:nuget/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a nuget Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from nuget and
    using it to create a new PackageDB entry. The package is then added to the
    scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    error_msg = map_nuget_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
