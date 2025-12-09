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
from typing import Iterable
from typing import Tuple
from typing import List

import requests
from packageurl import PackageURL
from aboutcode.hashid import get_core_purl


def fetch_cran_db(working_path, logger) -> Path:
    """
    Download the CRAN package database (~250MB JSON) in a memory-efficient way.
    Saves it to a file instead of loading everything into memory.
    """
    output_path = working_path / "cran_db.json"
    logger(f"Target download path: {output_path}")

    url = "https://crandb.r-pkg.org/-/all"
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    return output_path


def mine_cran_packageurls(db_path: Path) -> Iterable[Tuple[str, List[str]]]:
    """
    Extract package names and their versions from a CRAN DB JSON file.
    Yields a tuple: (base_purl, list_of_purls)
    ex:
    {
      "AATtools": {
      "_id": "AATtools",
      "_rev": "8-9ebb721d05b946f2b437b49e892c9e8c",
      "name": "AATtools",
      "versions": {
         "0.0.1": {...},
         "0.0.2": {...},
         "0.0.3": {...}
      }
    }
    """
    if not db_path.exists():
        raise FileNotFoundError(f"File not found: {db_path}")

    with open(db_path, encoding="utf-8") as f:
        data = json.load(f)

    for pkg_name, pkg_data in data.items():
        versions = list(pkg_data.get("versions", {}).keys())
        purls = []
        for version in versions:
            purl = PackageURL(
                type="cran",
                name=pkg_name,
                version=version,
            )
            purls.append(purl.to_string())

        base_purl = None
        if purls:
            first_purl = purls[0]
            base_purl = get_core_purl(first_purl)
        yield base_purl, purls
