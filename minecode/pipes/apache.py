#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import datetime, timezone

from minecode.pipes import fetch_checkpoint_from_github
from minecode.pipes import update_checkpoints_in_github
from minecode.pipes import MINECODE_PIPELINES_CONFIG_REPO

from minecode.utils import get_temp_dir

from packageurl import PackageURL

from scanpipe.pipes.federatedcode import clone_repository
from scanpipe.pipes.federatedcode import delete_local_clone

from scanpipe.pipes.fetch import fetch_http

import gzip
import shutil
import json
import os
import re

import requests


TRACE = False
TRACE_DEEP = False

SID_TYPE = "sid"


FIND_LS_URL = "https://archive.apache.org/dist/zzz/find-ls2.txt.gz"
PROJECT_JSON = "https://projects.apache.org/json/foundation/projects.json"
BASE_URL = "https://archive.apache.org/dist/"
BASE_NAMESPACE = "apache.org/"


PACKAGE_FILE_NAME = "ApachePackages.json"
COMPRESSED_PACKAGE_FILE_NAME = "ApachePackages.json.gz"
COMPRESSED_APACHE_PACKAGES_PATH = "apache/" + COMPRESSED_PACKAGE_FILE_NAME
APACHE_CHECKPOINT_PATH = "apache/checkpoints.json"
APACHE_PACKAGES_CHECKPOINT_PATH = "apache/packages_checkpoint.json"

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


def determine_purl_elements(path):
    """
    Determine and return the namespace, name, version and qualifier based
    on the path info
    """
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


def update_package_data(packages_data, packages_checksum):
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
    project_json_download = fetch_http(PROJECT_JSON)
    with open(project_json_download.path, encoding="utf-8") as f:
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
                    "mailing-list": "mailing_list",
                    "programming-language": "programming_language",
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


def mine_apache_packages(logger=None):
    """
    Mine apache packages names from "https://archive.apache.org/dist/zzz/find-ls2.txt.gz"

    Apache.org does not provide an index file, so we have no way
    to check the index and determine which packages are new and
    need to be synced, unlike npm.

    We will use the timestamp to log when the packages were mined.
    """

    config_repo = clone_repository(
        repo_url=MINECODE_PIPELINES_CONFIG_REPO,
        clone_path=get_temp_dir(),
        logger=logger,
    )

    packages_metadata = get_find_ls_archive_paths_and_metadata(logger=logger)

    last_mined_date = get_and_update_apache_checkpoints(
        cloned_repo=config_repo,
        checkpoint_path=APACHE_CHECKPOINT_PATH,
        logger=logger,
    )

    delete_local_clone(config_repo)

    return packages_metadata, last_mined_date


def get_find_ls_archive_paths_and_metadata(logger=None):
    """
    Get the archive paths and metadata from the find-ls file.
    """
    find_ls_download = fetch_http(FIND_LS_URL)
    txt_path = extract_archives(find_ls_download.path)
    packages_data, packages_checksum = get_archives_and_checksum(txt_path)
    packages_metadata = update_package_data(packages_data, packages_checksum)

    if logger:
        logger(f"Collected: {len(packages_metadata)} package archive files.")

    return packages_metadata


def get_and_update_apache_checkpoints(
    cloned_repo,
    checkpoint_path,
    config_repo=MINECODE_PIPELINES_CONFIG_REPO,
    logger=None,
):
    checkpoint = fetch_checkpoint_from_github(
        config_repo=config_repo,
        checkpoint_path=checkpoint_path,
    )

    last_mined_date = checkpoint.get("date", "")
    if logger:
        logger(f"Last mined date from checkpoint: {last_mined_date}")

    now = datetime.now(timezone.utc)
    formatted_now = now.strftime("%Y-%m-%d %H:%M UTC")
    checkpoint["date"] = formatted_now
    update_checkpoints_in_github(
        checkpoint=checkpoint,
        cloned_repo=cloned_repo,
        path=checkpoint_path,
        logger=logger,
    )

    return last_mined_date


def get_apache_packages_to_sync(packages_metadata, last_mined_date, logger=None):
    """
    Get the list of Apache packages that need to be synced based on the
    timestamp.

    Was thinking to record all mined archives, but even when processing
    only 10 packages it produced about 62k archive paths (all versions
    included) totaling 4.2 MB. Scaling this to all ~10,000 Apache packages
    would make the checkpoint file far too large. Instead, we will log only
    the timestamp indicating when the packages were mined.
    """

    if logger:
        logger(f"# of package archives found from apache.org: {len(packages_metadata)}")

    if not packages_metadata:
        return

    packages_to_sync = []
    for package in packages_metadata:
        path = package.get("filepath")
        release_date = package.get("date", "")
        if not last_mined_date:
            packages_to_sync.append(path)
        else:
            if release_date:
                fmt = "%Y-%m-%d %H:%M UTC"
                release_date_format = datetime.strptime(release_date, fmt).replace(
                    tzinfo=timezone.utc
                )
                last_mined_date_format = datetime.strptime(last_mined_date, fmt).replace(
                    tzinfo=timezone.utc
                )
                if release_date_format > last_mined_date_format:
                    packages_to_sync.append(path)
    if logger:
        logger(f"Starting initial package mining for {len(packages_to_sync)} packages archives.")

    return packages_to_sync


def mine_apache_packageurls(packages_to_sync, packages_metadata, logger=None):
    if logger:
        logger("Starting package mining for a batch of packages")

    handled_base = None
    for package_path in packages_to_sync:
        current_base = None
        current_purls = []
        purls_and_package_data = []

        if not package_path:
            continue

        # fetch packageURLs for package
        if logger:
            logger(f"getting packageURLs for package: {package_path}")

        package_path = package_path.lstrip("./")
        namespace, name, _version, _qualifiers = determine_purl_elements(package_path)
        current_base = PackageURL(
            type=SID_TYPE,
            namespace=namespace,
            name=name,
        ).to_string()

        if handled_base and handled_base == current_base:
            continue
        else:
            handled_base = current_base

        for package in packages_metadata:
            path = package.get("filepath").lstrip("./")
            package_namespace, package_name, package_version, package_qualifiers = (
                determine_purl_elements(path)
            )

            base_purl = PackageURL(
                type=SID_TYPE,
                namespace=package_namespace,
                name=package_name,
            ).to_string()

            if current_base == base_purl:
                purl = PackageURL(
                    type=SID_TYPE,
                    namespace=package_namespace,
                    name=package_name,
                    version=package_version,
                    qualifiers=package_qualifiers,
                ).to_string()

                if purl not in current_purls:
                    package_metadata = {}
                    package_metadata["name"] = package_name
                    package_metadata["version"] = package_version
                    package_metadata["repository_homepage_url"] = package.get(
                        "repository_homepage_url", ""
                    )
                    package_metadata["repository_download_url"] = package.get(
                        "repository_download_url", ""
                    )
                    package_metadata["description"] = package.get("description", "")
                    package_metadata["download_url"] = package.get("download_url", "")
                    package_metadata["size"] = package.get("size", "")
                    package_metadata["release_date"] = package.get("date", "")
                    package_metadata["mailing_list"] = package.get("mailing_list", "")
                    package_metadata["programming_language"] = package.get(
                        "programming_language", ""
                    )

                    package_data = (purl, package_metadata)

                    current_purls.append(purl)
                    purls_and_package_data.append(package_data)

            else:
                if current_purls:
                    yield current_base, current_purls, purls_and_package_data
                    # Reset
                    current_base = None
                    current_purls = []
                    purls_and_package_data = []
                    # packages_metadata should be ordered so that we can
                    # break the loop once all relevant entries have been
                    # found.
                    break

        if current_base is not None:
            yield current_base, current_purls, purls_and_package_data
