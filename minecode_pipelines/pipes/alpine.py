# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import os
from pathlib import Path

import base64
from packagedcode import models as scan_models
from scanpipe.pipes import federatedcode
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes.scancode import extract_archives

from minecode import debutils


ALPINE_APKINDEX_URL = "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/x86_64/APKINDEX.tar.gz"
ALPINE_CHECKPOINT_PATH = "alpine/checkpoints.json"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_ALPINE_REPO = "https://github.com/aboutcode-data/minecode-data-alpine-test"

# Number of packages
PACKAGE_BATCH_SIZE = 500


def build_packages(extracted_location, apk_download_url, purl=None):
    """
    Yield ScannedPackage built from Alpine Linux ( APK ) a `metadata` content
    """

    apk_index_file = Path(extracted_location) / "APKINDEX"

    with open(apk_index_file, encoding="utf-8") as f:
        parsed_pkginfo = parse_apkindex(f.read())

    extracted_pkginfo = get_package_by_name(parsed_pkginfo, purl.name)
    if not extracted_pkginfo:
        return

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
    apk_checksum = extracted_pkginfo.get("checksum")
    sha1 = apk_checksum_to_sha1(apk_checksum)

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
        sha1=sha1,
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
        if not line:
            if current_pkg:
                packages.append(current_pkg)
                current_pkg = {}
            continue

        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()

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

        if key in ("D", "p", "i"):
            current_pkg[field] = value.split()
        elif key in ("S", "I", "t", "k"):
            try:
                current_pkg[field] = int(value)
            except ValueError:
                current_pkg[field] = value
        else:
            current_pkg[field] = value

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


class AlpineCollector:
    """
    Download and process an Alpine APKINDEX.tar.gz file for Packages
    """

    def __init__(self, index_location=None):
        if index_location:
            self.index_location = index_location
        else:
            download_location = self._fetch_index()
            extract_archives(location=download_location)
            self.index_location = f"{download_location}-extract/"
        self.index_location_given = bool(index_location)

    def __del__(self):
        if self.index_location and not self.index_location_given:
            os.remove(self.index_location)

    def _fetch_index(self, uri=ALPINE_APKINDEX_URL):
        """
        Return a temporary location where the alpine index was saved.
        """
        index = fetch_http(uri)
        return index.path

    def get_packages(self, logger=None):
        """Yield Package objects from alpine index"""
        pass
