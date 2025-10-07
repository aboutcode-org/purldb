#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from minecode_pipelines.pipes.cargo import store_cargo_packages
from scanpipe.pipes.federatedcode import commit_and_push_changes
import json
from pathlib import Path

BATCH_SIZE = 1000
CARGO_CHECKPOINT_PATH = "cargo/checkpoints.json"


def process_cargo_packages(cargo_index_repo, cloned_data_repo, logger):
    """
    Process Cargo index files commit by commit.
    Push changes to fed_repo after:
    - every `commit_batch` commits, OR when reaching HEAD.
    """

    base_path = Path(cargo_index_repo.working_tree_dir)
    file_counter = 0
    purl_files = []
    purls = []

    for file_path in base_path.rglob("*"):
        if not file_path.is_file() or file_path.name in {
            "config.json",
            "README.md",
            "update-dl-url.yml",
        }:
            continue

        logger(f"Processing file: {file_path}")
        packages = []

        with open(file_path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    packages.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger(f"Skipping invalid JSON in {file_path} at line {line_number}: {e}")

        file_counter += 1

        result = store_cargo_packages(packages, cloned_data_repo)
        if result:
            purl_file, base_purl = result
            logger(f"Writing package URLs for package '{base_purl}' to {purl_file}")
            purl_files.append(purl_file)
            purls.append(str(base_purl))

        if file_counter % BATCH_SIZE == 0 and purl_files:
            commit_and_push_changes(
                repo=cloned_data_repo, files_to_commit=purl_files, purls=purls, logger=logger
            )
            purl_files.clear()
            purls.clear()

    if purl_files:
        commit_and_push_changes(
            repo=cloned_data_repo, files_to_commit=purl_files, purls=purls, logger=logger
        )
