#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import saneyaml

from pathlib import Path

from aboutcode.hashid import PURLS_FILENAME


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    write_data_to_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def write_data_to_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))
