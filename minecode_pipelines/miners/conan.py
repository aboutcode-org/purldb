#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
import saneyaml
from scanpipe.pipes.federatedcode import commit_changes
from scanpipe.pipes.federatedcode import push_changes
from minecode_pipelines import VERSION
from minecode_pipelines.pipes.conan import store_canon_packages

PACKAGE_BATCH_SIZE = 1000


def mine_and_publish_conan_packageurls(conan_index_repo, cloned_data_repo, logger):
    base_path = Path(conan_index_repo.working_dir)

    yml_files = []
    for file_path in base_path.glob("recipes/**/*"):
        if not file_path.name == "config.yml":
            continue
        yml_files.append(file_path)

    file_counter = 0
    purl_files = []
    purls = []

    for idx, file_path in enumerate(yml_files, start=1):
        package = file_path.parts[-2]
        with open(file_path, encoding="utf-8") as f:
            versions = saneyaml.load(f)

        if not versions:
            continue

        file_counter += 1
        push_commit = file_counter >= PACKAGE_BATCH_SIZE or idx == len(yml_files)

        result_store = store_canon_packages(package, versions, cloned_data_repo)
        if result_store:
            purl_file, base_purl = result_store
            logger(f"writing packageURLs for package: {base_purl} at: {purl_file}")

            purl_files.append(purl_file)
            purls.append(str(base_purl))

        if push_commit:
            commit_changes(
                repo=cloned_data_repo,
                files_to_commit=purl_files,
                purls=purls,
                mine_type="packageURL",
                tool_name="pkg:pypi/minecode-pipelines",
                tool_version=VERSION,
            )
            push_changes(repo=cloned_data_repo)
            file_counter = 0
