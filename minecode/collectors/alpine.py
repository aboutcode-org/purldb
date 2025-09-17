#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
from packageurl import PackageURL
from minecode import priority_router
from minecode.miners.alpine import build_packages
from minecode.utils import fetch_http, get_temp_file
from minecode.utils import extract_file
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_apk_package(package_url, pipelines, priority=0):
    """
    Add a Alpine Linux ( APK ) distribution `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    name = package_url.name
    version = package_url.version
    arch = package_url.qualifiers.get("arch")
    repo = package_url.qualifiers.get("repo")
    alpine_version = package_url.qualifiers.get("alpine_version")

    if not name or not version or not arch or not repo or not alpine_version:
        return None

    download_url = f"https://dl-cdn.alpinelinux.org/alpine/{alpine_version}/{repo}/{arch}/APKINDEX.tar.gz"
    apk_download_url = f"https://dl-cdn.alpinelinux.org/alpine/{alpine_version}/{repo}/{arch}/{name}-{version}.apk"

    content = fetch_http(download_url)
    location = get_temp_file("NonPersistentHttpVisitor")
    with open(location, "wb") as tmp:
        tmp.write(content)

    extracted_location = extract_file(location)

    packages = build_packages(extracted_location, apk_download_url, package_url)

    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:apk/.*")
def process_request(purl_str, **kwargs):
    """
    Process Alpine Linux ( APK ) Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_apk_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg