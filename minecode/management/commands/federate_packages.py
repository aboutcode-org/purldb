#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys
from pathlib import Path

from aboutcode.federated import DataFederation
from commoncode import fileutils
from minecode.management import federatedcode
from minecode.management.commands import VerboseCommand
from minecode_pipelines import pipes
from packagedb import models as packagedb_models

"""
Utility command to find license oddities.
"""
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


PACKAGE_BATCH_SIZE = 1000


def commit_message(commit_batch, total_commit_batch="many"):
    from django.conf import settings

    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/purldb"

    return f"""\
        Save PackageURLs from PurlDB ({commit_batch}/{total_commit_batch})

        Tool: {tool_name}@v{settings.PURLDB_VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


class Command(VerboseCommand):
    help = "Save and commit purls from PackageDB to FederatedCode repos."

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--working-directory",
            type=str,
            required=False,
            help="Directory where FederatedCode repos will be cloned",
        )

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        working_dir = options.get("working_directory")
        if working_dir:
            working_path = Path(working_dir)
        else:
            working_path = Path(fileutils.get_temp_dir())

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_cluster = data_federation.get_cluster("purls")

        # TODO: do something more efficient
        files_to_commit = []
        commit_batch = 1
        for i, package in enumerate(
            packagedb_models.Package.objects.all().iterator(chunk_size=PACKAGE_BATCH_SIZE), start=1
        ):
            package_repo_name, datafile_path = data_cluster.get_datafile_repo_and_path(
                purl=package.purl
            )
            _, package_repo = federatedcode.get_or_create_repository(
                repo_name=package_repo_name,
                working_path=working_path,
                logger=logger.log,
            )
            purl_file = pipes.write_packageurls_to_file(
                repo=package_repo,
                relative_datafile_path=datafile_path,
                packageurls=[package.purl],
                append=True,
            )
            if purl_file not in files_to_commit:
                files_to_commit.append(purl_file)

            if len(files_to_commit) == PACKAGE_BATCH_SIZE:
                federatedcode.commit_and_push_changes(
                    commit_message=commit_message(commit_batch),
                    repo=package_repo,
                    files_to_commit=files_to_commit,
                    logger=logger.log,
                )
                logger.log(f"Committed {i} purls to {package_repo_name}")
                files_to_commit.clear()
                commit_batch += 1

        if files_to_commit:
            federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_batch),
                repo=package_repo,
                files_to_commit=files_to_commit,
                logger=logger.log,
            )
            logger.log(f"Committed {i} purls to {package_repo_name}")
            files_to_commit.clear()
            commit_batch += 1
