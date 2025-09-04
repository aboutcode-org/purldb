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

from minecode_pipelines.pipes.cargo import store_cargo_packages
from minecode_pipelines.utils import get_changed_files


def process_cargo_packages(cargo_repo, fed_repo):
    base_path = Path(cargo_repo.working_tree_dir)
    valid_files = get_changed_files(cargo_repo)  # start from empty tree hash

    json_files = []
    for file_path in base_path.glob("**/*"):
        if not file_path.is_file() or file_path not in valid_files:
            continue

        if file_path.name in {"config.json", "README.md", "update-dl-url.yml"}:
            continue
        json_files.append(file_path)

    for idx, file_path in enumerate(json_files, start=1):
        try:
            with open(file_path, encoding="utf-8") as f:
                packages = []
                for line in f:
                    if line.strip():
                        packages.append(json.loads(line))

        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if packages:
            push_commit = idx == len(json_files)  # only True on last
            store_cargo_packages(packages, fed_repo, push_commit)
