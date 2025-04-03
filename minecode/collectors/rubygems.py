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
from minecode.miners.rubygems import build_rubygem_packages_from_api_v2_data

"""
Collect GEM packages from gem registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_package_json(name, version):
    """
    Return the contents of the JSON file of the package.
    """
    # Create the RubyGems API URL
    url = f"https://rubygems.org/api/v2/rubygems/{name}/versions/{version}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def get_all_package_version(name):
    """
    Return a list of all version numbers for the package name.
    """
    url = f"https://rubygems.org/api/v1/versions/{name}.json"
    try:
        versions = []
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Get all available versions
        for item in data:
            versions.append(item["number"])
        return versions
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_gem_package(package_url, pipelines, priority=0):
    """
    Add a gem `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    error = ""
    package_json = get_package_json(
        name=package_url.name,
        version=package_url.version,
    )

    if not package_json:
        error = f"Package does not exist on PyPI: {package_url}"
        logger.error(error)
        return error

    metadata = package_json
    packages = build_rubygem_packages_from_api_v2_data(metadata, package_url)
    # packages = build_packages(package_json, package_url)

    for package in packages:
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        # Submit package for scanning
        if db_package:
            add_package_to_scan_queue(
                package=db_package, pipelines=pipelines, priority=priority
            )

    return error


@priority_router.route("pkg:gem/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a gem Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from rubygem and
    using it to create a new PackageDB entry. The package is then added to the
    scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    if not package_url.version:
        versions = get_all_package_version(package_url.name)
        for version in versions:
            # package_url.version cannot be set as it will raise
            # AttributeError: can't set attribute
            # package_url.version = version
            purl = purl_str + "@" + version
            package_url = PackageURL.from_string(purl)
            error_msg = map_gem_package(package_url, pipelines, priority)

            if error_msg:
                return error_msg
    else:
        error_msg = map_gem_package(package_url, pipelines, priority)

        if error_msg:
            return error_msg
