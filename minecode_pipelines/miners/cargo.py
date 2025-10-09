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
from django.conf import settings
from scancodeio import VERSION
from aboutcode.pipeline import LoopProgress


def cargo_commit_message(commit_batch, total_commit_batch="many"):
    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/scancode.io"

    return f"""\
        Collect PackageURLs from crates.io index ({commit_batch}/{total_commit_batch})

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


def process_cargo_packages(cargo_index_repo, cloned_data_repo, logger):
    """Mine and publish Cargo PackageURLs from Crates.io package index."""

    base_path = Path(cargo_index_repo.working_tree_dir)
    batch_size = 4000
    file_counter = 0
    purl_files = []
    commit_count = 1

    package_dir = [p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
    package_paths = [f for dir in package_dir for f in dir.rglob("*") if f.is_file()]
    package_count = len(package_paths)

    progress = LoopProgress(
        total_iterations=package_count,
        logger=logger,
    )

    logger(f"Mine PackageURL for {package_count:,d} Cargo packages.")
    for path in progress.iter(package_paths):
        packages = []

        with open(path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    packages.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger(f"Skipping invalid JSON in {path} at line {line_number}: {e}")

        file_counter += 1
        result = store_cargo_packages(packages, cloned_data_repo)
        if result:
            purl_file, _ = result
            purl_files.append(purl_file)

        if file_counter % batch_size == 0 and purl_files:
            if commit_and_push_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                commit_message=cargo_commit_message(commit_count),
                logger=logger,
            ):
                commit_count += 1
            purl_files.clear()

    commit_and_push_changes(
        repo=cloned_data_repo,
        files_to_commit=purl_files,
        commit_message=cargo_commit_message(commit_count, commit_count),
        logger=logger,
    )
    logger(f"Processed PackageURL for {file_counter:,d} Cargo packages.")
    logger(f"Pushed new PackageURL in {commit_count:,d} commits.")
