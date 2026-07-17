#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import bz2
import json
import packagedcode.models as scan_models
from packageurl import PackageURL


def build_packages(location, download_url, package_info, package_identifier, package_url):
    """
    Yield ScannedPackage built from Conda API.
    """
    with bz2.open(location, "rt") as f:
        repodata = json.load(f)

    metadata_dict = repodata["packages"].get(package_identifier)
    if package_identifier.endswith(".conda"):
        metadata_dict = repodata["packages.conda"].get(package_identifier)

    if not metadata_dict:
        return

    download_data = dict(
        datasource_id="conda_api_metadata",
        type="conda",
        download_url=download_url,
    )

    extracted_license_statement = []
    license = metadata_dict.get("license")
    if license:
        extracted_license_statement.append(license)

    dependencies = []
    for dep in metadata_dict.get("depends", []):
        parts = dep.split()
        name = parts[0]

        dep_purl = PackageURL(type="conan", name=name)
        dep = scan_models.DependentPackage(purl=dep_purl.to_string())
        dependencies.append(dep)

    common_data = dict(
        name=package_url.name,
        namespace=package_url.namespace,
        version=package_url.version,
        sha256=metadata_dict.get("sha256"),
        md5=metadata_dict.get("md5"),
        size=metadata_dict.get("size"),
        extracted_license_statement=extracted_license_statement,
        dependencies=dependencies,
    )

    if package_url.namespace == "conda-forge" and package_info:
        description = package_info.get("description") or package_info.get("summary")
        html_url = package_info.get("html_url")
        dev_url = package_info.get("dev_url")

        license_conda_forge = package_info.get("license")
        if license_conda_forge:
            common_data["extracted_license_statement"].append(license_conda_forge)

        conda_forge_data = dict(
            description=description,
            homepage_url=html_url,
            repository_homepage_url=dev_url,
        )

        download_data.update(conda_forge_data)

    download_data.update(common_data)
    package = scan_models.PackageData.from_data(download_data)
    package.set_purl(package_url)
    yield package
