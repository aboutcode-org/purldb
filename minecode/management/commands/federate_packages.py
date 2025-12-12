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

from aboutcode.federated import DataFederation
from scanpipe.pipes import federatedcode
from minecode_pipelines import pipes
from minecode.management.commands import VerboseCommand
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

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


class Command(VerboseCommand):
    help = "Find packages with an ambiguous declared license."

    def add_arguments(self, parser):
        parser.add_argument("-i", "--input", type=str, help="Define the input file name")

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_cluster = data_federation.get_cluster("purls")

        # TODO: do something more efficient
        files_to_commit = []
        commit_batch = 1
        files_per_commit = PACKAGE_BATCH_SIZE
        for package in packagedb_models.Package.objects.all():
            package_repo, datafile_path = data_cluster.get_datafile_repo_and_path(purl=package.purl)
            purl_file = pipes.write_packageurls_to_file(
                repo=package_repo,
                relative_datafile_path=datafile_path,
                packageurls=[package.purl],
                append=True,
            )
            if purl_file not in files_to_commit:
                files_to_commit.append(purl_file)

            if len(files_to_commit) == files_per_commit:
                federatedcode.commit_and_push_changes(
                    commit_message=commit_message(commit_batch),
                    repo=package_repo,
                    files_to_commit=files_to_commit,
                    logger=logger,
                )
                files_to_commit.clear()
                commit_batch += 1

        if files_to_commit:
            federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_batch),
                repo=package_repo,
                files_to_commit=files_to_commit,
                logger=logger,
            )
