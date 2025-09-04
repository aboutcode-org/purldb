#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
from minecode_pipelines.pipes import conan
import saneyaml


def mine_and_publish_conan_packageurls(conan_repo, fed_repo):
    base_path = Path(conan_repo.working_dir)

    yml_files = []
    for file_path in base_path.glob("recipes/**/*"):
        if not file_path.name == "config.yml":
            continue
        yml_files.append(file_path)

    for idx, file_path in enumerate(yml_files, start=1):
        package = file_path.parts[-2]
        with open(file_path, encoding="utf-8") as f:
            versions = saneyaml.load(f)

        if versions:
            push_commit = idx == len(yml_files)  # only True on last
            conan.collect_and_write_purls_for_canon(package, versions, fed_repo, push_commit)
