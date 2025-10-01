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
from datetime import datetime
from shutil import rmtree

import debian_inspector
from aboutcode import hashid
from commoncode import fileutils
from commoncode.date import get_file_mtime
from packagedcode.models import PackageData
from packageurl import PackageURL
from scanpipe.pipes import federatedcode
from scanpipe.pipes.fetch import fetch_http

from minecode_pipelines import pipes
from minecode_pipelines import VERSION
from minecode_pipelines.pipes import ls


DEBIAN_CHECKPOINT_PATH = "debian/checkpoints.json"
DEBIAN_LSLR_URL = "http://ftp.debian.org/debian/ls-lR.gz"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_DEBIAN_REPO = "https://github.com/aboutcode-data/minecode-data-debian-test"

PACKAGE_BATCH_SIZE = 1000


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

    def __init__(self, index_location=None):
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
                previous_index_last_modified_date, "%Y-%m-%d %H:%M:%S"
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
                name, version, arch = debian_inspector.package.get_nva(file_name)
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
            yield versionless_purl, packaged_data


def commit_message(commit_batch, total_commit_batch="many"):
    from django.conf import settings

    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/scancode.io"

    return f"""\
        Collect PackageURLs from Debian ({commit_batch}/{total_commit_batch})

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


def collect_packages_from_debian(files_per_commit=PACKAGE_BATCH_SIZE, logger=None):
    # Clone data and config repo
    data_repo = federatedcode.clone_repository(
        repo_url=MINECODE_DATA_DEBIAN_REPO,
        logger=logger,
    )
    config_repo = federatedcode.clone_repository(
        repo_url=pipes.MINECODE_PIPELINES_CONFIG_REPO,
        logger=logger,
    )
    if logger:
        logger(f"{MINECODE_DATA_DEBIAN_REPO} repo cloned at: {data_repo.working_dir}")
        logger(f"{pipes.MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {config_repo.working_dir}")

    # get last_modified to see if we can skip files
    checkpoint = pipes.get_checkpoint_from_file(
        cloned_repo=config_repo, path=DEBIAN_CHECKPOINT_PATH
    )
    last_modified = checkpoint.get("previous_debian_index_last_modified_date")
    if logger:
        logger(f"previous_debian_index_last_modified_date: {last_modified}")

    # download and iterate through debian index
    debian_collector = DebianCollector()
    files_to_commit = []
    commit_batch = 1
    for current_purl, package in debian_collector.get_packages(
        previous_index_last_modified_date=last_modified
    ):
        # write packageURL to file
        package_base_dir = hashid.get_package_base_dir(purl=current_purl)
        purl_file = pipes.write_packageurls_to_file(
            repo=data_repo,
            base_dir=package_base_dir,
            packageurls=[package.purl],
            append=True,
        )
        if purl_file not in files_to_commit:
            files_to_commit.append(purl_file)

        if len(files_to_commit) == files_per_commit:
            federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_batch),
                repo=data_repo,
                files_to_commit=files_to_commit,
                logger=logger,
            )
            files_to_commit.clear()
            commit_batch += 1

    if files_to_commit:
        federatedcode.commit_and_push_changes(
            commit_message=commit_message(commit_batch),
            repo=data_repo,
            files_to_commit=files_to_commit,
            logger=logger,
        )

    last_modified = get_file_mtime(debian_collector.index_location)
    checkpoint = {"previous_debian_index_last_modified_date": last_modified}
    if logger:
        logger(f"checkpoint: {checkpoint}")
    pipes.update_checkpoints_in_github(
        checkpoint=checkpoint, cloned_repo=config_repo, path=DEBIAN_CHECKPOINT_PATH
    )

    repos_to_clean = [data_repo, config_repo]
    return repos_to_clean
