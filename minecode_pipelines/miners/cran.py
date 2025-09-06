#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from pathlib import Path
import requests


def get_cran_db(output_file="cran_db.json") -> Path:
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
