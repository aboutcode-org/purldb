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

from minecode import priority_router
from minecode.collectors.generic import map_fetchcode_supported_package
from minecode.collectors.gitlab import gitlab_get_all_package_version_author
from minecode.collectors.github import github_get_all_versions
from minecode.collectors.bitbucket import bitbucket_get_all_package_version_author
from minecode.miners.gitlab import build_packages_from_json_golang
from minecode.miners.golang import build_golang_generic_package
from minecode.miners.bitbucket import build_bitbucket_packages

from packageurl import PackageURL

from packagedb.models import PackageContentType

from urllib.parse import quote

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def extract_golang_subset_purl(purl_str):
    """
    Extract the first two segments after github.com or bitbucket.org and
    version For instance, pkg:golang/github.com/rickar/cal/v2/aa@2.1.23
    Return
        subset_path: rickar/cal
        version: 2.1.23
    """
    # Strip "pkg:golang/"
    purl_body = purl_str[len("pkg:golang/"):]

    # Extract namespace, name, and version
    parts = purl_body.split("/")
    version = ""
    if "@" in purl_str:
        version = purl_str.rpartition("@")[2]
    subset_path = parts[1] + "/" + parts[2].partition("@")[0]

    return subset_path, version


def gitlab_updated_purl(purl_str):
    """
    Return the path between "pkg:golang/gitlab.com/" and version with
    replacing "/" with "%2F" and version
    """
    version = ""
    if "@" in purl_str:
        version = purl_str.rpartition("@")[2]
    subset = purl_str.partition("pkg:golang/gitlab.com/")[2].partition("@")[0]
    subset_path = quote(subset, safe="")
    return subset_path, version


def get_package_versions(namespace_name):
    """
    Return all the version of the package fetched from "api.deps.dev" in a
    list
    """
    version_list = []
    url = f"https://api.deps.dev/v3/systems/GO/packages/{namespace_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        context = response.json()
        versions = context["versions"]
        for version in versions:
            version_list.append(version["versionKey"]["version"])
        return version_list
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def get_package_json(subset_path, type=None, version=None):
    """
    Return the contents of the JSON file of the package.
    """
    # Create URLs using purl fields
    if type == "gitlab":
        url = f"https://gitlab.com/api/v4/projects/{subset_path}"
    elif type == "bitbucket":
        url = f"https://api.bitbucket.org/2.0/repositories/{subset_path}"
    else:
        if version:
            if version.startswith('v'):
                url = f"https://api.deps.dev/v3/systems/GO/packages/{subset_path}/versions/{version}"
            else:
                url = f"https://api.deps.dev/v3/systems/GO/packages/{subset_path}/versions/v{version}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(response.json())
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def map_golang_package(package_url, package_json, pipelines, priority=0, filename=None):
    """
    Add a golang `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    error = ""

    if not package_json:
        error = f"Package does not exist: {package_url}"
        logger.error(error)
        return error

    purl_str = package_url.to_string()
    if purl_str.startswith("pkg:golang/gitlab"):
        packages = build_packages_from_json_golang(package_json, package_url)
    elif purl_str.startswith("pkg:golang/bitbucket"):
        packages = build_bitbucket_packages(package_json, package_url)
    else:
        packages = build_golang_generic_package(package_json, package_url)

    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(
            package, visit_level=0, filename=filename)
        if error:
            break

        # Submit package for scanning
        if db_package:
            add_package_to_scan_queue(
                package=db_package, pipelines=pipelines, priority=priority)

    return error


def process_download_metadata(download_url, package_json):
    """
    Return the download_url and the filename
    """
    response = requests.head(download_url, allow_redirects=True)
    redirected_download_url = response.url
    # Sometimes, the filename obtained from a
    # downloaded URL, even after following a redirect,
    # does not match the actual name of the downloaded
    # file. To retrieve the correct filename, it is
    # necessary to examine the "Content-Disposition"
    # header.
    content_disposition = response.headers.get("Content-Disposition")
    if content_disposition:
        filename = content_disposition.split("filename=")[-1].strip('"')
    else:
        filename = redirected_download_url.rpartition("/")[2]
    package_json["download_url"] = redirected_download_url

    return package_json, filename


# It may need indexing GitHub PURLs that requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route("pkg:golang/.*")
def process_requests(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a golang Package URL (PURL).

    This involves obtaining Package information for the PURL using
    https://github.com/aboutcode-org/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        """
        We retrieve metadata from APIs for GitHub, GitLab, and Bitbucket.
        For the other cases (or failing cases), we will get the data from
        deps.dev
        """
        processed = False
        if purl_str.startswith("pkg:golang/github"):
            subset_path, version = extract_golang_subset_purl(purl_str)
            if version:
                # Construct the GitHub purl
                github_purl = f"pkg:github/{subset_path}@{version}"
                package_url = PackageURL.from_string(github_purl)
                error_msg = map_fetchcode_supported_package(
                    package_url, pipelines, priority, from_go_lang=True
                )
                if error_msg:
                    print(error_msg)
                else:
                    processed = True
            else:
                version_list = github_get_all_versions(subset_path)
                for v in version_list:
                    # Construct the GitHub purl
                    # Strip the 'version' or 'v' from the collected version
                    if v.startswith("version"):
                        v = v.partition("version")[2]
                    elif v.startswith("v"):
                        v = v[1:]
                    github_purl = f"pkg:github/{subset_path}@{v}"
                    package_url = PackageURL.from_string(github_purl)
                    error_msg = map_fetchcode_supported_package(
                        package_url, pipelines, priority, from_go_lang=True
                    )
                    if error_msg:
                        print(error_msg)
                    else:
                        processed = True
        elif purl_str.startswith("pkg:golang/gitlab"):
            package_url = PackageURL.from_string(purl_str)
            subset_path, version = gitlab_updated_purl(purl_str)
            package_json = get_package_json(subset_path, "gitlab")
            if not package_json:
                error = f"package not found: {purl_str}"
            else:
                repo_version_author_list = gitlab_get_all_package_version_author(
                    subset_path)
                if repo_version_author_list:
                    for repo_version, author, email in repo_version_author_list:
                        # Check the version along with stripping the first
                        # character 'v' in the repo_version
                        if not version or version in {repo_version, repo_version[1:]}:
                            download_url = f"https://gitlab.com/api/v4/projects/{subset_path}/repository/archive.zip?sha={repo_version}"
                            updated_json, filename = process_download_metadata(
                                download_url, package_json
                            )
                            updated_json["author"] = author
                            updated_json["email"] = email
                            if not version:
                                if repo_version.startswith("v"):
                                    updated_purl_str = (
                                        PackageURL.to_string(
                                            package_url) + "@" + repo_version[1:])
                                else:
                                    updated_purl_str = (
                                        PackageURL.to_string(
                                            package_url) + "@" + repo_version)
                                updated_purl = PackageURL.from_string(
                                    updated_purl_str)
                                error_msg = map_golang_package(
                                    updated_purl, updated_json, pipelines, priority, filename=filename)
                                if error_msg:
                                    print(error_msg)
                                else:
                                    processed = True
                            else:
                                error_msg = map_golang_package(
                                    package_url, updated_json, pipelines, priority, filename=filename)
                                if error_msg:
                                    print(error_msg)
                                else:
                                    processed = True
                                break
                else:
                    # The repo does not have any tag (i.e. it only has one version)
                    download_url = (
                        f"https://gitlab.com/api/v4/projects/{subset_path}/repository/archive.zip"
                    )
                    updated_json, filename = process_download_metadata(
                        download_url, package_json)
                    error_msg = map_golang_package(
                        package_url, updated_json, pipelines, priority, filename=filename
                    )
                    if error_msg:
                        print(error_msg)
                    else:
                        processed = True
        elif purl_str.startswith("pkg:golang/bitbucket"):
            package_url = PackageURL.from_string(purl_str)
            subset_path, version = extract_golang_subset_purl(purl_str)
            package_json = get_package_json(subset_path, "bitbucket")
            if not package_json:
                error = f"package not found: {purl_str}"
            else:
                repo_version_author_list = bitbucket_get_all_package_version_author(
                    subset_path)
                package_json["repo_workspace_name"] = subset_path
                if repo_version_author_list:
                    found_match = False
                    for repo_version, author in repo_version_author_list:
                        # Check the version along with stripping the first
                        # character 'v' in the repo_version
                        if not version or version in {repo_version, repo_version[1:]}:
                            found_match = True
                            download_url = f"https://bitbucket.org/{subset_path}/get/{repo_version}.zip"
                            updated_json, filename = process_download_metadata(
                                download_url, package_json
                            )
                            updated_json["author"] = author
                            if not version:
                                if repo_version.startswith("v"):
                                    collected_version = repo_version[1:]
                                else:
                                    collected_version = repo_version
                                updated_purl_str = purl_str + "@" + collected_version
                                package_url = PackageURL.from_string(
                                    updated_purl_str)
                            error_msg = map_golang_package(
                                package_url, updated_json, pipelines, priority, filename=filename
                            )
                            if error_msg:
                                print(error_msg)
                            if version:
                                break
                    if not found_match:
                        error_msg = f"The package version not found: {version}"
                    else:
                        processed = True
                else:
                    # The repo does not have any tag (i.e. it only has one version)
                    # Get the main branch name for the download url
                    main_branch = package_json["mainbranch"]["name"]
                    download_url = f"https://bitbucket.org/{subset_path}/get/{main_branch}.zip"
                    updated_json, filename = process_download_metadata(
                        download_url, package_json)

                    error_msg = map_golang_package(
                        package_url, updated_json, pipelines, priority, filename=filename
                    )
                    if error_msg:
                        print(error_msg)
                    else:
                        processed = True
        if not processed:
            # Handle case which no version is in the input purl
            if '@' not in purl_str:
                namespace_name = purl_str.partition("pkg:golang/")[2]
                encoded_namespace_name = quote(namespace_name, safe="")
                version_list = get_package_versions(encoded_namespace_name)

                for version in version_list:
                    purl_str_version = purl_str + "@" + version
                    package_url = PackageURL.from_string(purl_str_version)
                    package_json = get_package_json(
                        encoded_namespace_name, version=version)
                    error_msg = map_golang_package(
                        package_url, package_json, pipelines, priority)
                    if error_msg:
                        print(error_msg)
            else:
                namespace_name = purl_str.partition(
                    "pkg:golang/")[2].rpartition("@")[0]
                encoded_namespace_name = quote(namespace_name, safe="")
                package_url = PackageURL.from_string(purl_str)
                package_json = get_package_json(
                    encoded_namespace_name, version=package_url.version)
                error_msg = map_golang_package(
                    package_url, package_json, pipelines, priority)
                if error_msg:
                    print(error_msg)

    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error
