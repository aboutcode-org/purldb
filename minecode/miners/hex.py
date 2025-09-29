#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
#

from packageurl import PackageURL
from packagedcode import models as scan_models
import requests
from packageurl.contrib.purl2url import build_hex_download_url

import logging

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def build_single_package(version_info, package_name, version, metadata_dict):
    """
    Return a PackageData object from a single pub.dev version_info dict.
    """
    description = metadata_dict.get("meta", {}).get("description")
    extracted_license_statement = metadata_dict.get("meta", {}).get("licenses")
    owners = metadata_dict.get("owners", [])
    created_at = metadata_dict.get("inserted_at")

    parties = []
    for owner in owners:
        parties.append(
            scan_models.Party(name=owner.get("username"), role="owner", email=owner.get("email"))
        )

    homepage_url = version_info.get("html_url")

    purl = PackageURL(
        type="hex",
        name=package_name,
        version=version,
    )

    package = scan_models.PackageData(
        type="hex",
        name=package_name,
        version=version,
        description=description,
        homepage_url=homepage_url,
        download_url=build_hex_download_url(str(purl)),
        parties=parties,
        sha256=version_info.get("checksum"),
        api_data_url=f"https://hex.pm/api/packages/{package_name}/releases/{version}",
        release_date=created_at,
        license_detections=extracted_license_statement,
    )
    package.datasource_id = "hex_api_metadata"
    package.set_purl(PackageURL(type="hex", name=package_name, version=version))
    return package


def build_packages(metadata_dict, purl):
    """
    Yield one or more PackageData objects from pub.dev metadata.
    If purl.version is set, use the single-version API response.
    Otherwise, use the all-versions API response.
    """
    if isinstance(purl, str):
        purl = PackageURL.from_string(purl)

    purl_version = purl.version
    package_name = purl.name

    if purl_version:
        url = f"https://hex.pm/api/packages/{package_name}/releases/{purl_version}"
        try:
            version_info = requests.get(url).json()
            yield build_single_package(
                version_info=version_info,
                package_name=package_name,
                version=purl_version,
                metadata_dict=metadata_dict,
            )
        except Exception:
            return iter([])
    else:
        releases = metadata_dict.get("releases", [])
        for release in releases:
            version = release.get("version")
            url = release.get("url")
            try:
                version_info = requests.get(url).json()
                yield build_single_package(
                    version_info=version_info,
                    package_name=package_name,
                    version=version,
                    metadata_dict=metadata_dict,
                )
            except Exception:
                logger.error(f"Failed to fetch or parse version info from {url}")
                continue
