#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
#

from packageurl import PackageURL
from packagedcode import models as scan_models


def build_single_package(version_info, package_name):
    """
    Build a single PackageData object from pub.dev version metadata.
    `version_info` is a dict, as returned under "versions" or from
    https://pub.dev/api/packages/<name>/versions/<version>
    """
    version = version_info.get("version")
    pubspec = version_info.get("pubspec", {}) or {}

    description = pubspec.get("description")
    homepage_url = pubspec.get("homepage")
    repository_url = pubspec.get("repository")
    issue_tracker = pubspec.get("issue_tracker")
    license_decl = pubspec.get("license")

    extracted_license_statement = []
    if license_decl and license_decl.lower() != "unknown":
        extracted_license_statement.append(license_decl)

    common_data = dict(
        name=package_name,
        version=version,
        description=description,
        homepage_url=homepage_url,
        repository_homepage_url=repository_url,
        bug_tracking_url=issue_tracker,
        extracted_license_statement=extracted_license_statement,
        parties=[],
    )

    archive_url = f"https://pub.dev/packages/{package_name}/versions/{version}.tar.gz"

    download_data = dict(
        datasource_id="pub_pkginfo",
        type="pub",
        download_url=archive_url,
    )
    download_data.update(common_data)

    package = scan_models.PackageData.from_data(download_data)
    package.datasource_id = "pub_api_metadata"
    package.set_purl(PackageURL(type="pub", name=package_name, version=version))

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
        package = build_single_package(metadata_dict, package_name)
        yield package
    else:
        versions = metadata_dict.get("versions", [])
        for version_info in versions:
            yield build_single_package(version_info, package_name)
