#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import saneyaml
from pathlib import Path
from unittest import TestCase

from minecode_pipelines.pipes.cran import mine_cran_packageurls

DATA_DIR = Path(__file__).parent.parent / "test_data" / "cran"


class CranPipelineTests(TestCase):
    def test_mine_cran_packageurls_from_testdata(self):
        """
        Ensure mine_cran_packageurls correctly parses the CRAN database
        and produces results identical to the expected YAML files.
        """

        db_file = DATA_DIR / "cran_db.json"
        results = list(mine_cran_packageurls(db_file))

        expected_files = [
            DATA_DIR / "expected_abbreviate.yaml",
            DATA_DIR / "expected_abc.data.yaml",
            DATA_DIR / "expected_abc.yaml",
        ]
        expected_base_purls = ["pkg:cran/abbreviate", "pkg:cran/abc", "pkg:cran/abc.data"]
        assert len(results) == len(expected_files)

        for result, expected_base_purl, expected_file in zip(
            results, expected_base_purls, expected_files
        ):
            with open(expected_file, encoding="utf-8") as f:
                expected_purls = saneyaml.load(f)

            base_purl, purls = result
            assert str(base_purl) == expected_base_purl
            assert purls == expected_purls
