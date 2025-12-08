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


import json
from pathlib import Path
from aboutcode.hashid import get_core_purl
from packageurl import PackageURL


def get_cargo_packages(packages):
    """Return base_purl and list of PackageURLs from cargo packages."""

    if not packages:
        return

    first_pkg = packages[0]
    name = first_pkg.get("name")
    version = first_pkg.get("vers")
    purl = PackageURL(type="cargo", name=name, version=version)
    base_purl = get_core_purl(purl)

    updated_purls = []
    for package in packages:
        name = package.get("name")
        version = package.get("vers")
        purl = PackageURL(type="cargo", name=name, version=version).to_string()
        updated_purls.append(purl)

    return base_purl, updated_purls


def mine_cargo_packageurls(cargo_index_repo, logger):
    """Mine Cargo PackageURLs from Crates.io package index."""

    base_path = Path(cargo_index_repo.working_tree_dir)
    package_dir = [p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
    package_paths = [f for dir in package_dir for f in dir.rglob("*") if f.is_file()]

    for path in package_paths:
        packages = []

        with open(path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    packages.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger(f"Skipping invalid JSON in {path} at line {line_number}: {e}")

        yield get_cargo_packages(packages)
