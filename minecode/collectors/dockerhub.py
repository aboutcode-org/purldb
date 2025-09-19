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
from minecode.miners.dockerhub import build_package_data
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def fetch_dockerhub_repo_metadata(name, namespace="library"):
    """
    Fetch repository metadata for a Docker Hub library image.
    Example: fetch_dockerhub_repo_metadata("nginx")
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{name}/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        logger.error(f"Error fetching repository metadata for {name}: {err}")
        return None


def fetch_dockerhub_tag_metadata(name, namespace, tag=None):
    """
    Search through Docker Hub tags for a given repository.
    - If `tag` is provided, return the JSON metadata for that tag (by name or digest).
    - If `tag` is None, return a list of all tag metadata.

    Examples:
        fetch_dockerhub_tag_metadata("nginx", "1.25.2")
        fetch_dockerhub_tag_metadata("nginx", "sha256:3d8957cb61d0223de2ab1aa2ec91d29796eb82a81cdcc1e968c090c29606d648")
        fetch_dockerhub_tag_metadata("nginx")  # returns all tags

    """
    page = 0
    page_size = 100
    all_results = []

    while True:
        page += 1
        url = f"https://hub.docker.com/v2/repositories/{namespace}/{name}/tags/?page={page}&page_size={page_size}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not tag:
                all_results.extend(results)  # collect everything
            else:
                for result in results:
                    if tag.startswith("sha256") and result.get("digest") == tag:
                        return [result]
                    elif result.get("name") == tag:
                        return [result]

            # Check if more pages exist
            if not data.get("next"):
                break  # no more pages

            if page_size * page > data.get("count", 0):
                break

        except requests.exceptions.RequestException as err:
            logger.error(f"Error fetching tags for {name}, page {page}: {err}")
            return None

    if not tag:
        return all_results  # return collected list

    return None  # tag not found


def map_dockerhub_package(package_url, pipelines, priority=0):
    """
    Add a Dockerhub distribution `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    if not package_url.name:
        error = f"Missing package name in DockerHub Package URL: {package_url}"
        logger.error(error)
        return error

    namespace = package_url.namespace or "library"
    package_metadata = fetch_dockerhub_repo_metadata(package_url.name, namespace)
    if not package_metadata:
        error = f"Package does not exist on dockerhub: {package_url}"
        logger.error(error)
        return error

    namespace = package_url.namespace or "library"

    package_tag_metadata = fetch_dockerhub_tag_metadata(
        package_url.name, namespace, package_url.version
    )
    package_metadata = {"pkg_metadata": package_metadata, "pkg_metadata_tags": package_tag_metadata}
    packages = build_package_data(package_metadata, package_url)

    error = None
    for package in packages:
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)
    return error


@priority_router.route("pkg:docker/.*")
def process_request(purl_str, **kwargs):
    """
    Process Dockerhub Package URL (PURL).
    ex:
    pkg:docker/nginx@latest
    pkg:docker/nginx@sha256:3d8957cb61d0223de2ab1aa2ec91d29796eb82a81cdcc1e968c090c29606d648
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    error_msg = map_dockerhub_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
