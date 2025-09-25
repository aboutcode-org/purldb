#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from datetime import datetime

from minecode_pipelines.pipes import get_checkpoint_from_file
from minecode_pipelines.pipes import get_commit_at_distance_ahead
from minecode_pipelines.pipes import update_checkpoints_in_github
from minecode_pipelines.pipes import get_changed_files
from minecode_pipelines.pipes.cargo import store_cargo_packages
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION

import json
from pathlib import Path


PACKAGE_BATCH_SIZE = 500
COMMIT_BATCH_SIZE = 10

CARGO_CHECKPOINT_PATH = "cargo/checkpoints.json"


def process_cargo_packages(cargo_index_repo, cloned_data_repo, config_repo, logger):
    """
    Process Cargo index files commit by commit.
    Push changes to fed_repo after:
    - every `commit_batch` commits, OR when reaching HEAD.
    """

    base_path = Path(cargo_index_repo.working_tree_dir)

    while True:
        cargo_checkpoints = get_checkpoint_from_file(
            cloned_repo=config_repo, path=CARGO_CHECKPOINT_PATH
        )

        checkpoints_last_commit = cargo_checkpoints.get("last_commit")

        try:
            next_commit = get_commit_at_distance_ahead(
                cargo_index_repo,
                checkpoints_last_commit,
                num_commits_ahead=COMMIT_BATCH_SIZE,
                branch_name="master",
            )
        except ValueError as e:
            logger(str(e))
            break

        if next_commit == checkpoints_last_commit:
            logger("No new commits to mine")
            break

        changed_files = get_changed_files(
            cargo_index_repo, commit_x=checkpoints_last_commit, commit_y=next_commit
        )
        logger(f"Found {len(changed_files)} changed files in Cargo index.")

        file_counter = 0
        purl_files = []
        purls = []
        for idx, rel_path in enumerate(changed_files):
            file_path = base_path / rel_path
            logger(f"Found {file_path}.")

            if not file_path.is_file() or file_path.name in {
                "config.json",
                "README.md",
                "update-dl-url.yml",
            }:
                continue

            packages = []
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            packages.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger(f"Skipping invalid JSON in {file_path}: {e}")

            file_counter += 1

            # Commit and push after each full batch or when processing the last file
            commit_and_push = (file_counter % PACKAGE_BATCH_SIZE == 0) or (
                idx == len(changed_files) - 1
            )

            result_store = store_cargo_packages(packages, cloned_data_repo)
            if result_store:
                purl_file, base_purl = result_store
                logger(f"writing packageURLs for package: {base_purl} at: {purl_file}")

                purl_files.append(purl_file)
                purls.append(str(base_purl))

            if not commit_and_push:
                continue

            commit_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                purls=purls,
                mine_type="packageURL",
                tool_name="pkg:pypi/minecode-pipelines",
                tool_version=VERSION,
            )

            push_changes(repo=cloned_data_repo)
            purl_files = []
            purls = []

            if logger:
                logger(
                    f"Updating checkpoint at: {CARGO_CHECKPOINT_PATH} with last commit: {checkpoints_last_commit}"
                )

            if next_commit != checkpoints_last_commit:
                settings_data = {
                    "date": str(datetime.now()),
                    "last_commit": next_commit,
                }

                update_checkpoints_in_github(
                    checkpoint=settings_data,
                    cloned_repo=config_repo,
                    path=CARGO_CHECKPOINT_PATH,
                )

        logger(f"Pushed batch for commit range {checkpoints_last_commit}:{next_commit}.")
