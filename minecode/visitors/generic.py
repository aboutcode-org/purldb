#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging

import attr
from fetchcode.package import info
from packagedcode.models import PackageData
from packageurl import PackageURL

from minecode import priority_router
from packagedb.models import PackageContentType

"""
Collect generic packages from a download URL.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_generic_package(package_url, pipelines, priority=0):
    """
    Add a generic `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    download_url = package_url.qualifiers.get("download_url")
    package = PackageData(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
        qualifiers=package_url.qualifiers,
        subpath=package_url.subpath,
        download_url=download_url,
        extra_data=dict(package_content=PackageContentType.BINARY),
    )

    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(
            package=db_package,
            pipelines=pipelines,
            priority=priority,
        )

    return error


@priority_router.route("pkg:generic/.*?download_url=.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a generic Package URL (PURL) with
    download_url as a qualifier
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occured when parsing {purl_str}: {e}"
        return error

    download_url = package_url.qualifiers.get("download_url")
    if not download_url:
        error = f"package_url {purl_str} does not contain a download_url qualifier"
        return error

    error_msg = map_generic_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg


def packagedata_from_dict(package_data):
    """
    Return a PackageData built from a `package_data` mapping.
    Ignore unknown and unsupported fields.
    """
    supported = {attr.name for attr in attr.fields(PackageData)}
    cleaned_package_data = {
        key: value for key, value in package_data.items() if key in supported
    }
    return PackageData.from_data(cleaned_package_data)


def map_fetchcode_supported_package(package_url, pipelines, priority=0):
    """
    Add a `package_url` supported by fetchcode to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    packages = [p for p in info(str(package_url)) or []]

    if not packages:
        error = f"Could not find package using fetchcode: {package_url}"
        logger.error(error)
        return error

    package_data = packages[0].to_dict()

    # Remove obsolete Package fields see https://github.com/aboutcode-org/fetchcode/issues/108
    package = packagedata_from_dict(package_data)

    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(
            package=db_package,
            pipelines=pipelines,
            priority=priority,
        )

    return error


GENERIC_FETCHCODE_SUPPORTED_PURLS = [
    "pkg:generic/busybox@.*",
    "pkg:generic/bzip2@.*",
    "pkg:generic/dnsmasq@.*",
    "pkg:generic/dropbear@.*",
    "pkg:generic/ebtables@.*",
    "pkg:generic/hostapd@.*",
    "pkg:generic/iproute2@.*",
    "pkg:generic/iptables@.*",
    "pkg:generic/libnl@.*",
    "pkg:generic/lighttpd@.*",
    "pkg:generic/nftables@.*",
    "pkg:generic/openssh@.*",
    "pkg:generic/samba@.*",
    "pkg:generic/syslinux@.*",
    "pkg:generic/toybox@.*",
    "pkg:generic/uclibc@.*",
    "pkg:generic/uclibc-ng@.*",
    "pkg:generic/util-linux@.*",
    "pkg:generic/wpa_supplicant@.*",
    "pkg:generic/ipkg@.*",
    "pkg:generic/linux@.*",
    "pkg:generic/mtd-utils@.*",
    "pkg:generic/barebox@.*",
    "pkg:generic/e2fsprogs@.*",
    "pkg:generic/udhcp@.*",
    "pkg:generic/miniupnpc@.*",
    "pkg:generic/miniupnpd@.*",
    "pkg:generic/minissdpd@.*",
    "pkg:generic/erofs-utils@.*",
]


# Indexing some generic PURLs requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route(*GENERIC_FETCHCODE_SUPPORTED_PURLS)
def process_request_fetchcode_generic(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a generic Package URL (PURL)
    supported by fetchcode.

    This involves obtaining Package information for the PURL using
    https://github.com/aboutcode-org/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error

    error_msg = map_fetchcode_supported_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
