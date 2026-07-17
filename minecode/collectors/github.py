#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packageurl import PackageURL

from minecode import priority_router
from minecode.collectors.generic import map_fetchcode_supported_package


def github_get_all_versions(subset_path):
    """
    Fetch all versions (tags) from a GitHub repository using the API
    Returns a list of all version tags in the repository
    """
    import requests

    url = f"https://api.github.com/repos/{subset_path}/tags"
    version_list = []
    page = 1

    while True:
        response = requests.get(
            url,
            params={"page": page, "per_page": 100},  # Max 100 per page
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        response.raise_for_status()

        data = response.json()
        if not data:
            break

        for tag in data:
            version = tag.get("name") or {}
            if version:
                version_list.append(version)
        page += 1

        # Check if we've reached the last page
        if "next" not in response.links:
            break

    return version_list


# Indexing GitHub PURLs requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route("pkg:github/.*")
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
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error

    error_msg = map_fetchcode_supported_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
