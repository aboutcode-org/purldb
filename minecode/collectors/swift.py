#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json
import logging
from packageurl import PackageURL
from minecode import priority_router
from minecode.miners import github
from minecode.miners.github import build_github_packages
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_swift_package(package_url, pipelines, priority=0):
    """
    Add a Swift distribution `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    namespace = package_url.namespace
    version = package_url.version

    owner_name = namespace.split("/")[-1]

    uri = f"https://api.github.com/repos/{owner_name}/{package_url.name}"
    _, response_text, _ = github.GithubSingleRepoVisitor(uri)
    repo_data = json.loads(response_text)
    repo_data["tags"] = [tag for tag in repo_data["tags"] if tag["name"] == version]
    packages = build_github_packages(json.dumps(repo_data), uri, package_url)

    error = None
    for package in packages:
        package.type = "swift"
        package.namespace = namespace
        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
        db_package, _, _, error = merge_or_create_package(package, visit_level=0)
        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)
    return error


@priority_router.route("pkg:swift/.*")
def process_request(purl_str, **kwargs):
    """
    Process Swift Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_swift_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
