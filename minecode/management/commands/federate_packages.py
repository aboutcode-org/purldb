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
from collections import defaultdict
from django.db.models import Q
from aboutcode.federated import DataFederation
from commoncode import fileutils
from minecode.management import federatedcode
from minecode.management.commands import VerboseCommand
from minecode import pipes
from packagedb import models as packagedb_models
from django.core.management.base import CommandError

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
        Save package data from PurlDB ({commit_batch}/{total_commit_batch})

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
        parser.add_argument(
            "--package-type",
            type=str,
            required=True,
            action="append",
            help="Type of package to be federated",
        )
        parser.add_argument(
            "--datakind",
            type=str,
            required=True,
            action="append",
            help="Kind of package data to be federated",
        )

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        working_dir = options.get("working_directory")
        if working_dir:
            working_path = Path(working_dir)
        else:
            working_path = Path(fileutils.get_temp_dir())

        package_types = options.get("package_type")
        package_types_query = Q()
        available_package_types = list(
            packagedb_models.Package.objects.order_by().values_list("type", flat=True).distinct()
        )
        for pt in package_types or []:
            if pt not in available_package_types:
                available_package_types_str = ", ".join(available_package_types)
                raise CommandError(
                    f"{pt} is not a valid package type. avaliable package types are: {available_package_types_str}"
                )
            package_types_query |= Q(type=pt)

        datakinds = options.get("datakind") or []
        available_datakinds = ["package_data", "purls"]
        for datakind in datakinds:
            if datakind not in available_datakinds:
                available_datakinds_str = ", ".join(available_datakinds)
                raise CommandError(
                    f"{datakind} is not a supported datakind. avaliable datakinds types are: {available_datakinds_str}"
                )

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_clusters = [data_federation.get_cluster(datakind) for datakind in datakinds]

        # TODO: do something more efficient
        files_to_commit_by_package_repo = defaultdict(list)
        number_of_files_commited_by_package_repo = {}
        commit_batch = 1
        for i, package in enumerate(
            packagedb_models.Package.objects.filter(package_types_query).iterator(
                chunk_size=PACKAGE_BATCH_SIZE
            ),
            start=1,
        ):
            for data_cluster in data_clusters:
                package_repo_name, datafile_path = data_cluster.get_datafile_repo_and_path(
                    purl=package.purl
                )
                files_to_commit = files_to_commit_by_package_repo[package_repo_name]

                _, package_repo = federatedcode.get_or_create_repository(
                    repo_name=package_repo_name,
                    working_path=working_path,
                    logger=logger.info,
                )
                if data_cluster.data_kind == "package_data":
                    data_kind_file = pipes.write_package_data_to_file(
                        repo=package_repo,
                        relative_api_package_metadata_datafile_path=datafile_path,
                        package_data=package.to_dict(),
                    )
                elif data_cluster.data_kind == "purls":
                    data_kind_file = pipes.write_packageurls_to_file(
                        repo=package_repo,
                        relative_datafile_path=datafile_path,
                        packageurls=[package.purl],
                        append=True,
                    )
                if data_kind_file not in files_to_commit:
                    files_to_commit.append(data_kind_file)

                number_of_files_to_commit = len(files_to_commit)
                if number_of_files_to_commit == PACKAGE_BATCH_SIZE:
                    number_of_files_commited = number_of_files_commited_by_package_repo.get(
                        package_repo_name, 0
                    )
                    total_number_of_files_commited = (
                        number_of_files_commited + number_of_files_to_commit
                    )
                    number_of_files_commited_by_package_repo[package_repo] = (
                        total_number_of_files_commited
                    )
                    federatedcode.commit_and_push_changes(
                        commit_message=commit_message(commit_batch),
                        repo=package_repo,
                        files_to_commit=files_to_commit,
                        logger=logger.info,
                    )
                    logger.info(
                        f"Committed {total_number_of_files_commited} files to {package_repo_name}"
                    )
                    files_to_commit.clear()
                    commit_batch += 1

        for package_repo, files_to_commit in files_to_commit_by_package_repo.items():
            if not files_to_commit:
                continue

            number_of_files_commited = number_of_files_commited_by_package_repo.get(
                package_repo_name, 0
            )
            total_number_of_files_commited = number_of_files_commited + number_of_files_to_commit
            number_of_files_commited_by_package_repo[package_repo] = total_number_of_files_commited
            federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_batch),
                repo=package_repo,
                files_to_commit=files_to_commit,
                logger=logger.info,
            )
            logger.info(f"Committed {total_number_of_files_commited} files to {package_repo_name}")
            files_to_commit.clear()
            commit_batch += 1
