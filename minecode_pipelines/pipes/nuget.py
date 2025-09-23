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

from packageurl import PackageURL

from scancodeio import VERSION


def get_catalog_page_count(catalog_index):
    if catalog_index.exists():
        with catalog_index.open("r", encoding="utf-8") as f:
            index = json.load(f)
            return index.get("count", 0)
    return 0


def collect_package_versions(events, package_versions, skipped_packages):
    for event in events or []:
        if event["@type"] != "nuget:PackageDetails":
            continue
        pkg_name = event["nuget:id"]
        if bool(re.fullmatch(r"[a-z0-9]{46}", pkg_name)):
            skipped_packages.add(pkg_name)
            continue

        purl = PackageURL(type="nuget", name=pkg_name).to_string()
        if purl not in package_versions:
            package_versions[purl] = set()

        package_versions[purl].add(event["nuget:version"])


def commit_message():
    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/scancode.io"

    return f"""\
        Collect PackageURLs from NuGet catalog

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """
