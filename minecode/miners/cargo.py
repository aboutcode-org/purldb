#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import requests
from packagedcode import models as scan_models


def build_packages(metadata_dict, purl):
    """
    Yield ScannedPackage built from crates.io.

    The metadata_dict is a dictionary. It consists of four primary
    components: crate, version, keywords, and categories. Among these, the
    version is the key focus, while the other three provide a summary of
    the package.

    purl: String value of the package url of the ResourceURI object
    """
    purl_version = purl.version
    versions = metadata_dict["versions"]
    for version_info in versions:
        version = version_info["num"]
        if purl_version and not purl_version == version:
            continue
        description = version_info["description"]
        name = version_info["crate"]
        homepage_url = version_info["homepage"]
        repository_homepage_url = version_info["repository"]

        extracted_license_statement = []
        lic = version_info["license"]
        if lic and lic != "UNKNOWN":
            extracted_license_statement.append(lic)

        kw = metadata_dict["crate"]["keywords"]

        # mapping of information that are common to all the downloads of a
        # version
        common_data = dict(
            name=name,
            version=version,
            description=description,
            homepage_url=homepage_url,
            repository_homepage_url=repository_homepage_url,
            extracted_license_statement=extracted_license_statement,
            keywords=kw,
        )

        if version_info["published_by"]:
            if version_info["published_by"]["name"]:
                author = version_info["published_by"]["name"]
            else:
                author = version_info["published_by"]["login"]

            if author:
                parties = common_data.get("parties")
                if not parties:
                    common_data["parties"] = []
                common_data["parties"].append(scan_models.Party(name=author, role="author"))

        download_path = version_info["dl_path"]
        if download_path:
            # As the  consistently ends with "/download" (e.g.,
            # "/api/v1/crates/purl/0.1.5/download"), we need to obtain the
            # redirected URL to ensure the filename is not simply
            # "download."
            download_url = "https://crates.io/" + download_path
            response = requests.head(download_url, allow_redirects=True)
            download_url = response.url

            download_data = dict(
                datasource_id="cargo_pkginfo",
                type="cargo",
                download_url=download_url,
                size=version_info["crate_size"],
                sha256=version_info["checksum"],
            )
            download_data.update(common_data)
            package = scan_models.PackageData.from_data(download_data)

            package.datasource_id = "cargo_api_metadata"
            package.set_purl(purl)
            yield package
