#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from minecode_pipelines.pipes import get_last_commit
from minecode_pipelines.pipes import get_changed_files
from minecode_pipelines.pipes import update_last_commit
from minecode_pipelines.pipes.cargo import store_cargo_packages
import json
from pathlib import Path

from minecode_pipelines.utils import get_next_x_commit


def process_cargo_packages(cargo_repo, fed_repo, fed_conf_repo, logger):
    """
    Process Cargo index files commit by commit.
    Push changes to fed_repo after:
    - every `commit_batch` commits, OR
    - when reaching HEAD.
    """

    base_path = Path(cargo_repo.working_tree_dir)

    while True:
        setting_last_commit = get_last_commit(fed_conf_repo, "cargo")
        next_commit = get_next_x_commit(cargo_repo, setting_last_commit, x=10, branch="master")

        if next_commit == setting_last_commit:
            logger("No new commits to mine")
            break

        changed_files = get_changed_files(
            cargo_repo, commit_x=setting_last_commit, commit_y=next_commit
        )
        logger(f"Found {len(changed_files)} changed files in Cargo index.")

        file_counter = 0
        for idx, rel_path in enumerate(changed_files):
            file_path = base_path / rel_path
            logger(f"Found {file_path}.")

            if not file_path.is_file():
                continue

            if file_path.name in {"config.json", "README.md", "update-dl-url.yml"}:
                continue

            packages = []
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        packages.append(json.loads(line))

            file_counter += 1
            push_commit = (file_counter % 1000 == 0) or (idx == len(changed_files))
            store_cargo_packages(packages, fed_repo, push_commit)

        update_last_commit(next_commit, fed_conf_repo, "cargo")
        logger(f"Pushed batch for commit range {setting_last_commit}:{next_commit}.")
