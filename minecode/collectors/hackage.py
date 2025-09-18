#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
from packageurl import PackageURL
import requests
from minecode import priority_router

from packagedb.models import PackageContentType
from packagedcode import models as scan_models

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def get_hackage_package_json(name):
    """
    Return the contents of the JSON file of the package from Hackage.
    Example: https://hackage.haskell.org/package/dplyr.json
    """
    url = f"https://hackage.haskell.org/package/{name}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as err:
        logger.error(f"Error fetching package data from Hackage: {err}")
        return None


def map_hackage_package(package_url, pipelines, priority=0):
    """
    Add a hackage `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    name = package_url.name
    version = package_url.version

    versions = get_hackage_package_json(name=name)
    if version not in versions:
        error = f"Version {version} not found for {name} on hackage"
        logger.error(error)
        return error

    download_url = f"https://hackage.haskell.org/package/{name}-{version}/{name}-{version}.tar.gz"
    homepage_url = f"https://hackage.haskell.org/package/{name}-{version}"

    package = scan_models.Package(
        type="hackage",
        name=name,
        version=version,
        download_url=download_url,
        homepage_url=homepage_url,
        primary_language="haskell",
    )

    package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    if db_package:
        add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:hackage/.*")
def process_request(purl_str, **kwargs):
    """
    Process Hackage Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_hackage_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
