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

from packageurl import PackageURL
import os
import textwrap
from pathlib import Path
import saneyaml
from aboutcode import hashid


ALLOWED_HOST = os.environ.get("FEDERATEDCODE_GIT_ALLOWED_HOST", "")
VERSION = os.environ.get("VERSION", "")
author_name = os.environ.get("FEDERATEDCODE_GIT_SERVICE_NAME", "")
author_email = os.environ.get("FEDERATEDCODE_GIT_SERVICE_EMAIL", "")
remote_name = os.environ.get("FEDERATEDCODE_GIT_REMOTE_NAME", "origin")


def collect_and_write_purls_for_canon(pacakge_name, versions_data, fed_repo, push_commit=False):
    """Collect Canon package versions into purls and write them to the repo."""

    base_purl = PackageURL(type="conan", name=pacakge_name)

    updated_purls = []
    versions = list(versions_data["versions"].keys())
    for version in versions:
        purl = PackageURL(type="conan", name=pacakge_name, version=version).to_string()
        updated_purls.append(purl)

    write_purls_to_repo(fed_repo, base_purl, updated_purls, push_commit)


def write_purls_to_repo(repo, package, updated_purls, push_commit=False):
    """Write or update package purls in the repo and optionally commit/push changes."""

    ppath = hashid.get_package_purls_yml_file_path(package)
    add_purl_result(updated_purls, repo, ppath)

    if push_commit:
        change_type = "Add" if ppath in repo.untracked_files else "Update"
        commit_message = f"""\
        {change_type} list of available {package} versions
        Tool: pkg:github/aboutcode-org/purldb@v{VERSION}
        Reference: https://{ALLOWED_HOST}/
        Signed-off-by: {author_name} <{author_email}>
        """

        default_branch = repo.active_branch.name
        repo.index.commit(textwrap.dedent(commit_message))
        repo.git.push(remote_name, default_branch, "--no-verify")


def add_purl_result(purls, repo, purls_file):
    """Add package urls result to the local Git repository."""
    relative_purl_file_path = Path(purls_file)

    write_to = Path(repo.working_dir) / relative_purl_file_path
    write_to.parent.mkdir(parents=True, exist_ok=True)

    with open(write_to, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(purls))

    repo.index.add([relative_purl_file_path])
    return relative_purl_file_path
