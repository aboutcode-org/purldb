#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
from urllib.parse import urljoin

import requests
from packageurl import PackageURL
from minecode import priority_router
from minecode.miners.conda import build_packages
from minecode.utils import fetch_http, get_temp_file
from packagedb.models import PackageContentType
from packageurl.contrib.purl2url import build_conda_download_url

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_conda_package(package_url, pipelines, priority=0):
    """
    Add a Conda distribution `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    download_url = build_conda_download_url(str(package_url))
    if not download_url:
        return None

    package_identifier = download_url.split("/")[-1]
    package_indexes_url = urljoin(download_url, "./repodata.json.bz2")

    content = fetch_http(package_indexes_url)
    location = get_temp_file("NonPersistentHttpVisitor")
    with open(location, "wb") as tmp:
        tmp.write(content)

    package_info = None
    if package_url.namespace == "conda-forge":
        package_info = get_package_info(package_url.name)
    packages = build_packages(location, download_url, package_info, package_identifier, package_url)

    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


def get_package_info(name):
    url = f"https://api.anaconda.org/package/conda-forge/{name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
        return None


@priority_router.route("pkg:conda/.*")
def process_request(purl_str, **kwargs):
    """
    Process Conda Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_conda_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
