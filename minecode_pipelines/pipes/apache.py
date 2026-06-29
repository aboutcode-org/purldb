#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import gzip
import shutil
import json
import os
from shutil import rmtree
import re

import requests

from packageurl import PackageURL


TRACE = False
TRACE_DEEP = False


FIND_LS_URL = "https://archive.apache.org/dist/zzz/find-ls2.txt.gz"
PROJECT_JSON = "https://projects.apache.org/json/foundation/projects.json"
BASE_URL = "https://archive.apache.org/dist/"
BASE_NAMESPACE = "apache.org/"


CHECKSUM_EXTS = (
    ".sha256",
    ".sha512",
    ".md5",
    ".sha",
    ".sha1",
)

# only keep downloads with certain extensions for some archives, packages and checksums
ARCHIVE_EXTS = (
    # archives
    ".jar",
    ".zip",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".war",
    ".tar.xz",
    ".tgz",
    ".tar",
    # packages
    # '.deb', '.rpm', '.msi', '.exe',
    ".whl",
    ".gem",
    ".nupkg",
    # '.dmg',
    # '.nbm',
)

IGNORED_PATH_CONTAINS = (
    "META/",  # #
    # doc
    "/documentation/",
    "/doc/",  # #
    "-doc.",  # #
    "-doc-",  # #
    "/docs/",  # #
    "-docs.",  # #
    "-docs-",  # #
    "javadoc",  # #
    "fulldoc",  # #
    "apidoc",  # #
    "-manual.",
    "-asdocs.",  # #
    # eclipse p2/update sites are redundant
    # redundant
    "updatesite/",  # #
    "eclipse-update-site",  # #
    "update/eclipse",  # #
    "sling/eclipse",  # #
    "eclipse.site-",
    # large multi-origin binary distributions
    "-distro.",
    "-bin-withdeps.",
    "-bin-with-deps",
    # these are larger distributions with third-parties
    "apache-airavata-distribution",
    "apache-airavata-server",
    "apache-mahout-distribution",
    "/syncope-standalone-",
    "binaries/conda",
    # obscure
    "perl/contrib",
    # index data
    "zzz",
    # doc
    "ant/manual",
    # tmp
    "/tmp/",  # noqa: S108 safe: used only as ignore pattern
)


# TODO: ignore these globs too:

# openoffice/*/binaries is very large
# /*/apache-log4j-*-site.zip


class ApacheCollector:
    """
    Download and process the find-ls file.
    """

    def __init__(
        self,
        find_ls_url=None,
        project_json=None,
        logger=None,
    ):
        self.downloads = []

        if not find_ls_url:
            find_ls_url = FIND_LS_URL

        if not project_json:
            project_json = PROJECT_JSON

        find_ls_download = self._fetch_http(find_ls_url)
        project_json_download = self._fetch_http(project_json)
        self.find_ls_location = find_ls_download.path
        self.project_json_location = project_json_download.path

    def __del__(self):
        if self.downloads:
            for download in self.downloads:
                rmtree(download.directory)

    def _fetch_http(self, uri):
        from scanpipe.pipes.fetch import fetch_http

        fetched = fetch_http(uri)
        self.downloads.append(fetched)
        return fetched

    def get_packages(self):
        """Yield Package objects from the find_ls list"""
        txt_path = extract_archives(archive_path=self.find_ls_location)
        packages_data, packages_checksum = get_archives_and_checksum(txt_path)
        updated_packages_list = update_package_data(
            packages_data, packages_checksum, project_json_location=self.project_json_location
        )

        current_base = None
        current_purls = []

        for package in updated_packages_list:
            """
            repository_homepage_url = package.get("repository_homepage_url", "")
            repository_download_url = package.get("repository_download_url", "")
            download_url = package.get("download_url", "")
            size = package.get("size", "")
            release_date = package.get("date", "")
            """
            namespace, name, version, qualifiers = determine_purl_elements(package)

            purl = PackageURL(
                type="sid",
                namespace=namespace,
                name=name,
                version=version,
                qualifiers=qualifiers,
            ).to_string()

            base_purl = PackageURL(
                type="sid",
                namespace=namespace,
                name=name,
            ).to_string()

            if current_base is None:
                current_base = base_purl
                current_purls.append(purl)
            elif base_purl == current_base:
                current_purls.append(purl)
            else:
                yield current_base, current_purls, []
                current_base = base_purl
                current_purls = [purl]

        if current_base is not None:
            yield current_base, current_purls, []


def determine_purl_elements(package):
    """
    Determine and return the namespace, name, version and qualifier based
    on the path info
    """
    path = package.get("filepath").lstrip("./")
    parsed_result = parse_apache_path_common(path)
    if parsed_result:
        namespace = BASE_NAMESPACE + parsed_result.get("namespace")
        name = parsed_result.get("name")
        version = parsed_result.get("version")
        qualifier = {"file_name": parsed_result["file_name"]}
    else:
        parsed_result = parse_apache_path_complex(path)
        namespace = BASE_NAMESPACE + parsed_result.get("namespace")
        name = parsed_result.get("name")
        version = parsed_result.get("version")
        qualifier = {"download_url": BASE_URL + path}
    return namespace, name, version, qualifier


def get_archives_and_checksum(txt_path):
    """
    Return:
    - A list of dictionaries containing the package archive path, size, and release date
    - A list of checksum files

    """
    packages_data = []
    packages_checksum = []
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()

            if not parts or len(parts) < 9:
                continue

            # Extracting the components
            permissions = parts[0]

            # Skip if it's not a file
            if not permissions.startswith("-"):
                continue

            size = parts[4]
            date = f"{parts[5]} {parts[6]} {parts[7]}"
            filepath = parts[8]

            if any(ignored in filepath for ignored in IGNORED_PATH_CONTAINS):
                continue

            if filepath.endswith(CHECKSUM_EXTS):
                packages_checksum.append(filepath)
            elif filepath.endswith(ARCHIVE_EXTS):
                info_dict = {}
                info_dict["filepath"] = filepath
                info_dict["size"] = size
                info_dict["date"] = date
                packages_data.append(info_dict)

    return packages_data, packages_checksum


def update_package_data(packages_data, packages_checksum, project_json_location):
    """
    Update package metadata with:
    - Project information from
    https://projects.apache.org/json/foundation/projects.json
    (homepage, download page, description).
    - A constructed download URL.
    - Available checksum values (sha256, sha512, md5, etc.).
    """
    updated_package_data = []
    data = ""
    with open(project_json_location, encoding="utf-8") as f:
        data = json.load(f)

    for package in packages_data:
        package_dict = package.copy()
        path = package["filepath"]
        package_name = path.split("/")[1]
        download_url = BASE_URL + path.lstrip("./")
        package_dict["download_url"] = download_url
        if data:
            package_metadata = data.get(package_name, "")
            # In some cases, projects.json uses
            # {package_name}-{subpackage_name} as the key.
            # For example, "directory-fortress" likely refers to
            # files under /directory/fortress*
            if not package_metadata:
                subpackage_name = path.split("/")[2]
                name = package_name + "-" + subpackage_name
                package_metadata = data.get(name, "")
            if package_metadata:
                for key, target in {
                    "homepage": "repository_homepage_url",
                    "download-page": "repository_download_url",
                    "description": "description",
                }.items():
                    value = package_metadata.get(key)
                    if value:
                        package_dict[target] = value
        """
        Request to get checksum for every packages will likely lead to Rate Limiting/HTTP 429 error
        Ignoring the checksum collection for now
        """
        # for ext in CHECKSUM_EXTS:
        #    checksum_path = path + ext
        #    if checksum_path in packages_checksum:
        #        checksum = get_checksum(BASE_URL + checksum_path.lstrip("./"))
        #        checksum_ext = ext.lstrip(".")
        #        package_dict[checksum_ext] = checksum

        updated_package_data.append(package_dict)
    return updated_package_data


def get_checksum(url):
    """
    Fetch the checksum file from the given URL and
    return only the hash value.
    """
    response = requests.get(url)
    response.raise_for_status()

    content = response.text.strip()
    checksum = content.split()[0]
    return checksum


def extract_archives(archive_path):
    txt_path = os.path.splitext(archive_path)[0]

    # Open the gzipped file and write out the decompressed content
    with gzip.open(archive_path, "rb") as f_in:
        with open(txt_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return txt_path


def parse_apache_path_common(path):
    """
    Parse standard Apache paths following a strict
    '{name}/{version}/{filename}' structure. Requires the version segment
    to start with a digit and the component name to be a substring of the
    filename.
    """
    segments = path.strip().split("/")

    # The minimum required segments for {name}/{version}/{filename} is 3
    if len(segments) < 3:
        return None

    # filename is the last segment of the path
    file_name = segments[-1]

    # version is the segment before the filename
    version = segments[-2]

    # Check if the version segment represents a numeric value (starts with
    # a digit)
    if not (version and version[0].isdigit()):
        return None

    # name is the segment before the version
    name = segments[-3]

    # namespace consists of all segments from the beginning up to the name
    # segment
    namespace_segments = segments[:-3]
    namespace = "/".join(namespace_segments)

    return {"namespace": namespace, "name": name, "version": version, "file_name": file_name}


def parse_apache_path_complex(path):
    """
    Parse non-standard Apache paths by locating a version or keyword
    boundary.

    Scans left-to-right for a "marker" segment (a semantic version or words
    like 'bin', 'rc1'). The segment right before this marker becomes the
    'name'. Falls back to the parent directory if no marker is found.
    """
    segments = path.strip().split("/")

    if len(segments) < 2:
        return None

    path_segments = segments[:-1]
    file_name = segments[-1]

    special_words = {
        "jars",
        "binaries",
        "binary",
        "sources",
        "source",
        "java",
        "bin",
        "dist",
        "old",
        "obsolete",
    }

    marker_idx = None
    version = ""

    for i, seg in enumerate(path_segments):
        # Match standard versions (e.g., 1.2.0) OR release candidates (e.g., rc1, rc1.1)
        # Added re.IGNORECASE to safely handle 'RC1' or 'rc1'
        version_match = re.search(r"(\d+(?:\.\d+)+|rc\d+(?:\.\d+)*)", seg, re.IGNORECASE)

        is_version = False
        if version_match:
            is_version = True
            if not version:
                version = version_match.group(1)

        # Check only against the hardcoded metadata keywords
        is_special = seg.lower() in special_words

        if (is_version or is_special) and marker_idx is None:
            marker_idx = i

    if marker_idx is not None and marker_idx > 0:
        name = path_segments[marker_idx - 1]
        namespace_segments = path_segments[: marker_idx - 1]
    else:
        name = path_segments[-1] if path_segments else ""
        namespace_segments = path_segments[:-1] if path_segments else []

    namespace = "/".join(namespace_segments)

    return {"namespace": namespace, "name": name, "version": version, "file_name": file_name}
