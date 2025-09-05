#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from minecode_pipelines.pipes import get_last_commit, get_changed_files, update_last_commit
from minecode_pipelines.pipes.cargo import store_cargo_packages
import json
from pathlib import Path


def process_cargo_packages(cargo_repo, fed_repo, logger):
    base_path = Path(cargo_repo.working_tree_dir)
    setting_last_commit = get_last_commit(fed_repo, "cargo")
    valid_files = get_changed_files(cargo_repo, setting_last_commit)  # start from empty tree hash

    logger(f"Found {len(valid_files)} changed files in Cargo index.")
    targets_files = []
    for file_path in base_path.glob("**/*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(base_path))
        if rel_path not in valid_files:
            continue

        if file_path.name in {"config.json", "README.md", "update-dl-url.yml"}:
            continue

        targets_files.append(file_path)

    logger(f"Collected {len(targets_files)} target package files to process.")

    for idx, file_path in enumerate(targets_files, start=1):
        packages = []
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    packages.append(json.loads(line))

        if not packages:
            continue

        push_commit = idx == len(targets_files)  # only True on last
        store_cargo_packages(packages, fed_repo, push_commit)
        logger(f"Processed {len(packages)} packages from {file_path} ({idx}/{len(targets_files)}).")

    update_last_commit(setting_last_commit, fed_repo, "cargo")
    logger("Updated last commit checkpoint for Cargo.")
