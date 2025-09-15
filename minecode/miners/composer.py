#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packagedcode import models as scan_models


def build_packages(metadata_dict, purl):
    """
    Yield ScannedPackage built from packagist.org API.

    metadata_dict format:
      {
        "packages": {
          "vendor/package": [
             { version metadata... }
          ]
        }
      }
    """
    purl_version = purl.version
    package_name = f"{purl.namespace}/{purl.name}" if purl.namespace else purl.name

    packages = metadata_dict.get("packages") or {}
    versions = packages.get(package_name) or []

    for version_info in versions:
        version_normalized = version_info.get("version_normalized")
        version = version_info.get("version")
        if purl_version and not (purl_version == version or purl_version == version_normalized):
            continue

        description = version_info.get("description")
        homepage_url = version_info.get("homepage")
        repository_url = version_info.get("source", {}).get("url")

        extracted_license_statement = version_info.get("license") or []

        authors = version_info.get("authors", [])
        parties = []
        for author in authors:
            parties.append(scan_models.Party(name=author.get("name"), role="author"))

        dist = version_info.get("dist", {})
        download_url = dist.get("url")
        sha1 = dist.get("shasum")

        common_data = dict(
            name=purl.name,
            version=version,
            description=description,
            homepage_url=homepage_url,
            repository_homepage_url=repository_url,
            extracted_license_statement=extracted_license_statement,
            parties=parties,
        )

        if download_url:
            download_data = dict(
                datasource_id="composer_pkginfo",
                type="composer",
                download_url=download_url,
                sha1=sha1,
            )
            download_data.update(common_data)
            package = scan_models.PackageData.from_data(download_data)
            package.datasource_id = "composer_api_metadata"
            package.set_purl(purl)
            yield package
