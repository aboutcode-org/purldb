#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from packageurl import PackageURL

from minecode import debutils
from minecode.msys2 import parse_pkginfo
from pathlib import Path
from packagedcode import models as scan_models


def build_packages(extracted_location, download_url, purl=None):
    """
    Yield ScannedPackage built from Arch Linux a `metadata` content
    """

    build_file = Path(extracted_location) / ".BUILDINFO"
    pkginfo_file = Path(extracted_location) / ".PKGINFO"

    with open(pkginfo_file, encoding="utf-8") as f:
        extracted_pkginfo = parse_pkginfo(f.read())

    with open(build_file, encoding="utf-8") as f:
        extracted_build = parse_pkginfo(f.read())

    description = extracted_pkginfo.get("desc")
    version = extracted_pkginfo.get("version")
    extracted_license_statement = extracted_pkginfo.get("licenses")

    parties = []
    maintainers = extracted_build.get("packager")
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            party = scan_models.Party(name=name, role="maintainer", email=email)
            parties.append(party)

    repository_homepage_url = extracted_pkginfo.get("url")
    size = extracted_pkginfo.get("size")
    sha256 = extracted_build.get("pkgbuild_sha256sum")

    dependencies = []
    for name in extracted_pkginfo.get("depends", []):
        dep_purl = PackageURL(type="alpm", name=name)
        dep = scan_models.DependentPackage(purl=dep_purl.to_string())
        dependencies.append(dep)

    download_data = dict(
        type="alpm",
        name=purl.name,
        version=version,
        qualifiers=purl.qualifiers,
        description=description,
        repository_homepage_url=repository_homepage_url,
        extracted_license_statement=extracted_license_statement,
        parties=parties,
        size=size,
        sha256=sha256,
        dependencies=dependencies,
        download_url=download_url,
    )

    package = scan_models.PackageData.from_data(download_data)
    package.datasource_id = "alpm_metadata"
    package.set_purl(purl)
    yield package
