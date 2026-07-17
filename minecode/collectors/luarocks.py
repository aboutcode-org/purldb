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
import requests
from minecode import priority_router

from packagedb.models import PackageContentType
from packageurl.contrib.purl2url import build_luarocks_download_url
from packagedcode import models as scan_models

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_lua_package(package_url, pipelines, priority=0):
    """
    Add a lua `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    namespace = package_url.namespace
    name = package_url.name
    version = package_url.version

    download_url = build_luarocks_download_url(str(package_url))

    try:
        response = requests.head(download_url)
        if response.status_code != 200:
            error = f"Package does not exist on luarocks.org: {package_url}"
            logger.error(error)
            return error
    except requests.RequestException as e:
        error = f"Error checking package existence on luarocks.org: {package_url}, error: {e}"
        logger.error(error)
        return error

    package = scan_models.Package(
        type="luarocks",
        namespace=namespace,
        name=name,
        version=version,
        download_url=download_url,
        homepage_url=f"https://luarocks.org/modules/{namespace}/{name}"
        if namespace
        else f"https://luarocks.org/modules/{name}",
        primary_language="lua",
    )

    package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    if db_package:
        add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:luarocks/.*")
def process_request(purl_str, **kwargs):
    """
    Process Luarocks Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_lua_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
