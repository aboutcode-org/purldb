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

from packageurl import PackageURL


MESON_WRAPDB_RELEASES_URL = (
    "https://raw.githubusercontent.com/mesonbuild/wrapdb/master/releases.json"
)


def get_meson_packages(package_name, package_data):
    """
    Return a tuple of (base_purl, [versioned_purl_strings]) for a single
    Meson WrapDB package entry from ``releases.json``.

    The ``package_data`` dict has the structure::

        {
            "dependency_names": ["dep1", "dep2"],
            "versions": ["1.0.0-1", "1.0.0-2", ...]
        }

    WrapDB versions use a ``-N`` suffix to denote build recipe revisions that
    are specific to the WrapDB and do not exist upstream.
    """
    base_purl = PackageURL(type="meson", name=package_name)
    versions = package_data.get("versions") or []
    versioned_purls = [
        PackageURL(
            type="meson",
            name=package_name,
            version=str(version),
        ).to_string()
        for version in versions
    ]
    return base_purl, versioned_purls


def mine_meson_packageurls(wrapdb_repo, logger):
    """
    Yield ``(base_purl, [versioned_purl_strings])`` tuples from a cloned
    Meson WrapDB repository by parsing its ``releases.json``.
    """
    releases_path = Path(wrapdb_repo.working_dir) / "releases.json"
    if not releases_path.exists():
        logger(f"releases.json not found at {releases_path}")
        return

    with open(releases_path, encoding="utf-8") as f:
        releases = json.load(f)

    for package_name, package_data in releases.items():
        if not package_data:
            continue
        yield get_meson_packages(
            package_name=package_name,
            package_data=package_data,
        )
