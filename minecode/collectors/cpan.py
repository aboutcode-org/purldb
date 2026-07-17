#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import requests
from packageurl import PackageURL

from minecode import priority_router
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_cpan_release_json(distribution, version):
    """
    Return the MetaCPAN release JSON for a given distribution@version.

    Example:
    https://fastapi.metacpan.org/v1/release/_search?q=distribution:Mojolicious%20AND%20version:9.22

    """
    url = (
        f"https://fastapi.metacpan.org/v1/release/_search?"
        f"q=distribution:{distribution}%20AND%20version:{version}"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json()
        hits = results.get("hits", {}).get("hits", [])
        if not hits:
            return None
        return hits[0].get("_source")
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
        return None


def map_cpan_package(package_url, pipelines, priority=0):
    """
    Add a CPAN distribution `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package
    from minecode.miners.cpan import build_packages

    name = package_url.name
    version = package_url.version
    release_json = get_cpan_release_json(name, version)

    if not release_json:
        error = f"Distribution does not exist on CPAN: {package_url}"
        logger.error(error)
        return error

    packages = build_packages(release_json, package_url)

    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:cpan/.*")
def process_request(purl_str, **kwargs):
    """
    Process CPAN Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_cpan_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
