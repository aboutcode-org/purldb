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

import gzip
import logging
from datetime import datetime
from shutil import rmtree
from traceback import format_exc as traceback_format_exc

import debian_inspector
from commoncode import fileutils
from packagedcode.models import PackageData
from packageurl import PackageURL
from scanpipe.pipes.fetch import fetch_http

from minecode_pipelines.pipes import ls

DEBIAN_LSLR_URL = "http://ftp.debian.org/debian/ls-lR.gz"


def is_collectible(file_name):
    """Return True if a `file_name` is collectible."""
    # 'Contents-*.gz' are mapping/indexes of installed files to the actual package that provides them.
    # TODO: add tests!

    return file_name and (
        file_name
        in (
            "Packages.gz",
            "Release",
            "Sources.gz",
        )
        or file_name.endswith(
            (
                ".deb",
                ".dsc",
            )
        )
        or (file_name.startswith("Contents-") and file_name.endswith(".gz"))
    )


def is_debian_url(uri):
    return "debian.org" in uri


def is_ubuntu_url(uri):
    return "ubuntu" in uri


class DebianCollector:
    """
    Download and process a Debian ls-lR.gz file for Packages
    """

    def __init__(self, logger, index_location=None):
        self.logger = logger
        self.downloads = []
        if index_location:
            self.index_location = index_location
        else:
            index_download = self._fetch_index()
            self.index_location = index_download.path

    def __del__(self):
        if self.downloads:
            for download in self.downloads:
                rmtree(download.directory)

    def _fetch_http(self, uri):
        fetched = fetch_http(uri)
        self.downloads.append(fetched)
        return fetched

    def _fetch_index(self, uri=DEBIAN_LSLR_URL):
        """
        Fetch the Debian index at `uri` and return a Download with information
        about where it was saved.
        """
        index = self._fetch_http(uri)
        return index

    def get_packages(self, previous_index_last_modified_date=None, logger=None):
        """Yield Package objects from debian index"""
        with gzip.open(self.index_location, "rt") as f:
            content = f.read()

        url_template = DEBIAN_LSLR_URL.replace("ls-lR.gz", "{path}")
        if previous_index_last_modified_date:
            previous_index_last_modified_date = datetime.strptime(
                previous_index_last_modified_date, "%Y-%m-%d %H:%M:%S.%f"
            )
        for entry in ls.parse_directory_listing(content):
            entry_date = None
            if entry.date:
                entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
            if (entry.type != ls.FILE) or (
                previous_index_last_modified_date
                and entry_date
                and (entry_date <= previous_index_last_modified_date)
            ):
                continue

            path = entry.path.lstrip("/")
            file_name = fileutils.file_name(path)

            if not is_collectible(file_name):
                continue

            if file_name.endswith((".deb", ".udeb", ".tar.gz", ".tar.xz", ".tar.bz2", ".tar.lzma")):
                try:
                    name, version, arch = debian_inspector.package.get_nva(file_name)
                except Exception as e:
                    self.logger(
                        f"Failed to get PURL field from: {file_name} with error {e!r}:\n{traceback_format_exc()}",
                        level=logging.ERROR,
                    )

                package_url = PackageURL(
                    type="deb",
                    namespace="debian",
                    name=name,
                    version=str(version),
                    qualifiers=dict(arch=arch) if arch else None,
                )
            else:
                package_url = None

            if not package_url:
                continue

            versionless_purl = PackageURL(
                type=package_url.type,
                namespace=package_url.namespace,
                name=package_url.name,
            )
            packaged_data = PackageData(
                type=package_url.type,
                namespace=package_url.namespace,
                name=package_url.name,
                version=package_url.version,
                qualifiers=package_url.qualifiers,
                size=entry.size,
                download_url=url_template.format(path=path),
            )
            yield versionless_purl, [packaged_data.purl]
