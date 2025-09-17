#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from minecode import debutils
from pathlib import Path
from packagedcode import models as scan_models
import base64


def build_packages(extracted_location, apk_download_url, purl=None):
    """
    Yield ScannedPackage built from Alpine Linux ( APK ) a `metadata` content
    """

    apk_index_file = Path(extracted_location) / "APKINDEX"
    
    with open(apk_index_file, encoding="utf-8") as f:
        parsed_pkginfo = parse_apkindex(f.read())

    extracted_pkginfo = get_package_by_name(parsed_pkginfo, purl.name)

    description = extracted_pkginfo.get("description")
    version = extracted_pkginfo.get("version")
    extracted_license_statement = extracted_pkginfo.get("license")

    parties = []
    maintainers = extracted_pkginfo.get("maintainer")
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            party = scan_models.Party(name=name, role="maintainer", email=email)
            parties.append(party)

    repository_homepage_url = extracted_pkginfo.get("url")
    size = extracted_pkginfo.get("size")
    # apk_checksum = extracted_pkginfo.get("checksum")
    # sha1 = apk_checksum_to_sha1(apk_checksum)

    # dependencies = []
    # for name in extracted_pkginfo.get("depends", []):
    #     dep_purl = PackageURL(type="apk", name=name)
    #     dep = scan_models.DependentPackage(purl=dep_purl.to_string())
    #     dependencies.append(dep)

    download_data = dict(
        type="apk",
        name=purl.name,
        version=version,
        qualifiers=purl.qualifiers,
        description=description,
        repository_homepage_url=repository_homepage_url,
        extracted_license_statement=extracted_license_statement,
        parties=parties,
        size=size,
        # sha1=sha1,
        # dependencies=dependencies,
        download_url=apk_download_url,
    )

    package = scan_models.PackageData.from_data(download_data)
    package.datasource_id = "alpine_metadata"
    package.set_purl(purl)
    yield package



def parse_apkindex(data: str):
    """
    Parse an APKINDEX format string into a list of package dictionaries.
    https://wiki.alpinelinux.org/wiki/Apk_spec
    """
    packages = []
    current_pkg = {}

    for line in data.splitlines():
        line = line.strip()
        if not line:  # blank line = end of one package entry
            if current_pkg:
                packages.append(current_pkg)
                current_pkg = {}
            continue

        # key:value
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()

        # Map known fields
        mapping = {
            "C": "checksum",
            "P": "name",
            "V": "version",
            "A": "arch",
            "S": "size",
            "I": "installed_size",
            "T": "description",
            "U": "url",
            "L": "license",
            "o": "origin",
            "m": "maintainer",
            "t": "build_time",
            "c": "commit",
            "k": "provider_priority",
            "D": "depends",
            "p": "provides",
            "i": "install_if",
        }

        field = mapping.get(key, key)
        # Dependencies and lists should be split
        if key in ("D", "p", "i"):
            current_pkg[field] = value.split()
        elif key in ("S", "I", "t", "k"):
            try:
                current_pkg[field] = int(value)
            except ValueError:
                current_pkg[field] = value
        else:
            current_pkg[field] = value

    # Add last package if not already added
    if current_pkg:
        packages.append(current_pkg)

    return packages

def get_package_by_name(packages, name):
    return next((pkg for pkg in packages if pkg["name"] == name), None)

def apk_checksum_to_sha1(apk_checksum: str) -> str:
    """
    Convert an Alpine APKINDEX package checksum (Q1... format)
    into its SHA-1 hex digest.
    """
    if not apk_checksum.startswith("Q1"):
        raise ValueError("Invalid checksum format: must start with 'Q1'")

    # Drop the "Q1" prefix
    b64_part = apk_checksum[2:]

    # Decode from base64
    sha1_bytes = base64.b64decode(b64_part)

    # Convert to hex
    return sha1_bytes.hex()