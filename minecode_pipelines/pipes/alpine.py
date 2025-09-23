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

from shutil import rmtree
from pathlib import Path

import base64
from packageurl import PackageURL
from packagedcode.models import PackageData, Party
from scanpipe.pipes import federatedcode
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes.scancode import extract_archives

from minecode import debutils


ALPINE_CHECKPOINT_PATH = "alpine/checkpoints.json"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_ALPINE_REPO = "https://github.com/aboutcode-data/minecode-data-alpine-test"

# Number of packages
PACKAGE_BATCH_SIZE = 500
ALPINE_LINUX_DISTROS = [
    "edge",
    "latest-stable",
    "v3.0",
    "v3.1",
    "v3.10",
    "v3.11",
    "v3.12",
    "v3.13",
    "v3.14",
    "v3.15",
    "v3.16",
    "v3.17",
    "v3.18",
    "v3.19",
    "v3.2",
    "v3.20",
    "v3.21",
    "v3.22",
    "v3.3",
    "v3.4",
    "v3.5",
    "v3.6",
    "v3.7",
    "v3.8",
    "v3.9",
]
ALPINE_LINUX_REPOS = [
    "community",
    "main",
    "releases",
    "testing",
]
ALPINE_LINUX_ARCHS = [
    "aarch64",
    "armhf",
    "armv7",
    "ppc64le",
    "s390x",
    "x86",
    "x86_64",
]


def build_package(extracted_pkginfo, distro=None):
    name = extracted_pkginfo.get("name")
    version = extracted_pkginfo.get("version")
    arch = extracted_pkginfo.get("arch")
    qualifiers = {
        "arch": arch,
    }
    if distro:
        qualifiers.update({"distro": distro})

    parties = []
    maintainers = extracted_pkginfo.get("maintainer")
    if maintainers:
        name, email = debutils.parse_email(maintainers)
        if name:
            party = Party(name=name, role="maintainer", email=email)
            parties.append(party)

    description = extracted_pkginfo.get("description")
    extracted_license_statement = extracted_pkginfo.get("license")
    repository_homepage_url = extracted_pkginfo.get("url")
    size = extracted_pkginfo.get("size")
    apk_checksum = extracted_pkginfo.get("checksum")
    sha1 = apk_checksum_to_sha1(apk_checksum)
    apk_download_url = f"https://dl-cdn.alpinelinux.org/alpine/{distro}/main/{arch}/{name}-{version}.apk"

    purl = PackageURL(
        type="apk",
        namespace="alpine",
        name=name,
        version=version,
        qualifiers=qualifiers
    )
    download_data = dict(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=purl.version,
        qualifiers=purl.qualifiers,
        description=description,
        repository_homepage_url=repository_homepage_url,
        extracted_license_statement=extracted_license_statement,
        parties=parties,
        size=size,
        sha1=sha1,
        download_url=apk_download_url,
        datasource_id = "alpine_metadata",
    )
    package = PackageData.from_data(download_data)

    return package


def parse_apkindex(data: str):
    """
    Parse an APKINDEX format string into a list of package dictionaries.
    https://wiki.alpinelinux.org/wiki/Apk_spec
    """
    current_pkg = {}

    for line in data.splitlines():
        line = line.strip()
        if not line:
            if current_pkg:
                yield current_pkg
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
        yield current_pkg


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

    def __init__(self):
        self.index_downloads = []

    def __del__(self):
        if self.index_downloads:
            for download in self.index_downloads:
                rmtree(download.directory)

    def _fetch_index(self, uri):
        """
        Return a temporary location where the alpine index was saved.
        """
        index = fetch_http(uri)
        self.index_downloads.append(index)
        return index

    def get_packages(self, logger=None):
        """Yield Package objects from alpine index"""

        url_template = "https://dl-cdn.alpinelinux.org/alpine/{distro}/{suite}/{arch}/APKINDEX.tar.gz"

        for distro in ALPINE_LINUX_DISTROS:
            for suite in ALPINE_LINUX_REPOS:
                for arch in ALPINE_LINUX_ARCHS:
                    index_download_url = url_template.format(distro=distro, suite=suite, arch=arch)
                    index = self._fetch_index(uri=index_download_url)
                    extract_archives(location=index.path)
                    index_location = f"{index.path}-extract/APKINDEX"
                    with open(index_location, encoding="utf-8") as f:
                        for pkg in parse_apkindex(f.read()):
                            pd = build_package(pkg, distro=distro)
                            current_purl = PackageURL(
                                type=pd.type,
                                namespace=pd.namespace,
                                name=pd.name,
                            )
                            yield current_purl, pd
