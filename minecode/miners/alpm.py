#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from minecode import debutils
from minecode.msys2 import parse_pkginfo
from pathlib import Path
from packagedcode import models as scan_models


def build_packages(extracted_location, download_url, purl=None):
    """ """

    build_file = Path(extracted_location) / ".BUILDINFO"
    pkginfo_file = Path(extracted_location) / ".PKGINFO"

    with open(pkginfo_file, encoding="utf-8") as f:
        extracted_pkginfo = parse_pkginfo(f.read())

    with open(build_file, encoding="utf-8") as f:
        extracted_build = parse_pkginfo(f.read())

    description = extracted_pkginfo["desc"]
    version = extracted_pkginfo["version"]
    extracted_license_statement = extracted_pkginfo["licenses"]

    parties = []
    maintainers = extracted_build["packager"]
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            party = scan_models.Party(name=name, role="maintainer", email=email)
            parties.append(party)

    dependencies = extracted_pkginfo["depends"]
    repository_homepage_url = extracted_pkginfo["url"]
    release_date = extracted_pkginfo["builddate"]
    size = extracted_pkginfo["size"]
    sha256 = extracted_build["pkgbuild_sha256sum"]

    download_data = dict(
        name=purl.name,
        version=version,
        description=description,
        repository_homepage_url=repository_homepage_url,
        extracted_license_statement=extracted_license_statement,
        parties=parties,
        size=size,
        sha256=sha256,
        # dependencies=dependencies,
        # release_date=datetime.utcfromtimestamp(release_date),
        download_url=download_url,
    )

    package = scan_models.PackageData.from_data(download_data)
    package.datasource_id = "alpm_metadata"
    package.set_purl(purl)
    yield package
