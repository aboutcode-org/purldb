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
# under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an “AS IS” BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.


import json
import re

from django.conf import settings

from minecode_pipelines.pipes import write_packageurls_to_file
from packageurl import PackageURL

from aboutcode.hashid import get_package_base_dir
from aboutcode.pipeline import LoopProgress
from scancodeio import VERSION

NUGET_PURL_METADATA_REPO = "https://github.com/aboutcode-data/minecode-data-nuget-test"


def get_catalog_page_count(catalog_index):
    if catalog_index.exists():
        with catalog_index.open("r", encoding="utf-8") as f:
            index = json.load(f)
            return index.get("count", 0)
    return 0


def collect_package_versions(events, package_versions, skipped_packages):
    """Collect package versions from events in the NuGet package catalog."""
    for event in events or []:
        if event["@type"] != "nuget:PackageDetails":
            continue
        pkg_name = event["nuget:id"]

        # Skip package names that resemble NuGet API key and can't be pushed to GitHub.
        if bool(re.fullmatch(r"oy2[a-z0-9]{43}", pkg_name)):
            skipped_packages.add(pkg_name)
            continue

        purl = PackageURL(type="nuget", name=pkg_name).to_string()
        if purl not in package_versions:
            package_versions[purl] = set()

        package_versions[purl].add(event["nuget:version"])


def mine_nuget_package_versions(catalog_path, logger):
    """Mine NuGet package and versions from NuGet catalog."""
    catalog = catalog_path / "catalog"
    catalog_count = get_catalog_page_count(catalog / "index.json")
    catalog_pages = catalog / "pages"

    package_versions = {}
    skipped_packages = set()
    logger(f"Collecting versions from {catalog_count:,d} NuGet catalog.")
    progress = LoopProgress(total_iterations=catalog_count, logger=logger)
    for page in progress.iter(catalog_pages.rglob("*.json")):
        with page.open("r", encoding="utf-8") as f:
            page_catalog = json.load(f)

        collect_package_versions(
            events=page_catalog["items"],
            package_versions=package_versions,
            skipped_packages=skipped_packages,
        )
    logger(f"Collected versions for {len(package_versions):,d} NuGet package.")
    return package_versions, skipped_packages


def commit_message(commit_batch, total_commit_batch="many"):
    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/scancode.io"

    return f"""\
        Collect PackageURLs from NuGet catalog ({commit_batch}/{total_commit_batch})

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


def get_nuget_purls_from_versions(base_purl, versions):
    """Return PURLs for a NuGet `base_purls` from set of `versions`."""
    purl_dict = PackageURL.from_string(base_purl).to_dict()
    del purl_dict["version"]
    return [PackageURL(**purl_dict, version=v).to_string() for v in versions]


def mine_and_publish_nuget_packageurls(package_versions, logger):
    """Mine and publish PackageURLs from NuGet package versions."""
    from scanpipe.pipes import federatedcode

    cloned_repo = federatedcode.clone_repository(
        repo_url=NUGET_PURL_METADATA_REPO,
        logger=logger,
    )
    file_to_commit = []
    batch_size = 4000
    file_processed = 0
    commit_count = 1
    nuget_package_count = len(package_versions)
    progress = LoopProgress(
        total_iterations=nuget_package_count,
        logger=logger,
        progress_step=1,
    )

    logger(f"Mine packageURL for {nuget_package_count:,d} NuGet packages.")
    for base, versions in progress.iter(package_versions.items()):
        package_base_dir = get_package_base_dir(purl=base)
        packageurls = get_nuget_purls_from_versions(base_purl=base, versions=versions)

        purl_file = write_packageurls_to_file(
            repo=cloned_repo,
            base_dir=package_base_dir,
            packageurls=sorted(packageurls),
        )
        file_to_commit.append(purl_file)
        file_processed += 1

        if len(file_to_commit) > batch_size:
            if federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_count),
                repo=cloned_repo,
                files_to_commit=file_to_commit,
                logger=logger,
            ):
                commit_count += 1
            file_to_commit.clear()

    federatedcode.commit_and_push_changes(
        commit_message=commit_message(
            commit_batch=commit_count,
            total_commit_batch=commit_count,
        ),
        repo=cloned_repo,
        files_to_commit=file_to_commit,
        logger=logger,
    )
    logger(f"Processed PackageURL for {file_processed:,d} NuGet packages.")
    logger(f"Pushed new PackageURL in {commit_count:,d} commits.")
    federatedcode.delete_local_clone(repo=cloned_repo)
