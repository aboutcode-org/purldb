#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import logging

import requests

from packageurl import PackageURL

from minecode import priority_router
from minecode.collectors.generic import map_fetchcode_supported_package
from minecode.miners.golang import build_packages_from_gitlab


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def extract_golang_purl(purl):
    """
    Extract the name, namespace and version of a given purl.
    """
    # Strip "pkg:golang/"
    purl_body = purl[len("pkg:golang/") :]

    # Extract namespace, name, and version
    parts = purl_body.split("/")
    version = parts[-1].split("@")[-1]
    namespace = parts[1]
    name = parts[2].partition("@")[0]

    return namespace, name, version


def gitlab_get_package_json(namespace, name):
    """
    Return the contents of the JSON file of the package.
    """
    # Create URLs using purl fields
    url = f"https://gitlab.com/api/v4/projects/{namespace}%2F{name}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def gitlab_get_all_package_version_author(namespace, name):
    """
    Return a list of all version numbers along with author and author email
    for the package.
    """
    repo_tags = f"https://gitlab.com/api/v4/projects/{namespace}%2F{name}/repository/tags"
    try:
        response = requests.get(repo_tags)
        response.raise_for_status()
        data = response.json()
        version_author_list = []
        # Get all available versions
        for item in data:
            if not item["release"]:
                continue
            version = item["release"]["tag_name"]
            author = item["commit"]["author_name"]
            author_email = item["commit"]["author_email"]
            version_author_list.append((version, author, author_email))
        return version_author_list
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_golang_package(package_url, package_json, pipelines, priority=0):
    """
    Add a pypi `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    error = ""

    if not package_json:
        error = f"Package does not exist on PyPI: {package_url}"
        logger.error(error)
        return error

    packages = build_packages_from_gitlab(package_json, package_url)

    for package in packages:
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        # Submit package for scanning
        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


# It may need indexing GitHub PURLs that requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route("pkg:golang/.*")
def process_request_dir_listed(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a GitHub Package URL (PURL).

    This involves obtaining Package information for the PURL using
    https://github.com/aboutcode-org/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        # FIXME: This is not working for some reasons.
        # It'll work if I input the same updated_purl_str in the UI
        namespace, name, version = extract_golang_purl(purl_str)
        if purl_str.startswith("pkg:golang/github"):
            # Construct the GitHub purl
            github_purl = f"pkg:github/{namespace}/{name}@{version}"
            package_url = PackageURL.from_string(github_purl)
            error_msg = map_fetchcode_supported_package(package_url, pipelines, priority)
            if error_msg:
                return error_msg
        elif purl_str.startswith("pkg:golang/gitlab"):
            package_url = PackageURL.from_string(purl_str)
            package_json = gitlab_get_package_json(namespace, name)
            repo_version_author_list = gitlab_get_all_package_version_author(namespace, name)
            if version:
                for repo_version, author, email in repo_version_author_list:
                    # Check the version along with stripping the first
                    # character 'v' in the repo_version
                    if version == repo_version or version == repo_version[1:]:
                        download_url = f"https://gitlab.com/api/v4/projects/{namespace}%2F{name}/repository/archive.zip?sha={repo_version}"
                        response = requests.head(download_url, allow_redirects=True)
                        redirected_download_url = response.url
                        package_json["download_url"] = redirected_download_url
                        package_json["author"] = author
                        package_json["email"] = email
                        error_msg = map_golang_package(
                            package_url, package_json, pipelines, priority
                        )
                        break
            else:
                for repo_version, author, email in repo_version_author_list:
                    download_url = f"https://gitlab.com/api/v4/projects/{namespace}%2F{name}/repository/archive.zip?sha={repo_version}"
                    response = requests.head(download_url, allow_redirects=True)
                    redirected_download_url = response.url
                    package_json["download_url"] = redirected_download_url
                    package_json["author"] = author
                    package_json["email"] = email
                    error_msg = map_golang_package(package_url, package_json, pipelines, priority)

    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error
