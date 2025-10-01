#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json
from pathlib import Path
import requests
from packageurl import PackageURL


def fetch_cran_db(output_file="cran_db.json") -> Path:
    """
    Download the CRAN package database (~250MB JSON) in a memory-efficient way.
    Saves it to a file instead of loading everything into memory.
    """

    url = "https://crandb.r-pkg.org/-/all"
    output_path = Path(output_file)

    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    return output_path


def extract_cran_packages(json_file_path: str) -> list:
    """
    Extract package names and their versions from a CRAN DB JSON file.
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
    db_path = Path(json_file_path)
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
        yield purls
