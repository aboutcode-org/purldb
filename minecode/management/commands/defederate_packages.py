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
import tempfile

import os
from commoncode.fileutils import walk
from aboutcode.federated import DataFederation
from minecode_pipelines import pipes
from minecode.management.commands import VerboseCommand
from packagedb import models as packagedb_models
from packageurl import PackageURL
import saneyaml

"""
Utility command to find license oddities.
"""
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


def yield_purls_from_yaml_files(location):
    for root, _, files in walk(location):
        for file in files:
            if not (file == "purls.yml"):
                continue
            fp = os.path.join(root, file)
            with open(fp) as f:
                purl_strs = saneyaml.load(f.read()) or []
            for purl_str in purl_strs:
                yield PackageURL.from_string(purl_str)


class Command(VerboseCommand):
    help = "Find packages with an ambiguous declared license."

    def add_arguments(self, parser):
        parser.add_argument("-i", "--input", type=str, help="Define the input file name")

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        working_path = tempfile.mkdtemp()

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_cluster = data_federation.get_cluster("purls")

        checked_out_repos = {}
        for purl_type, data_repository in data_cluster._data_repositories_by_purl_type.items():
            repo_name = data_repository.name
            checked_out_repos[repo_name] = pipes.init_local_checkout(
                repo_name=repo_name,
                working_path=working_path,
                logger=logger,
            )

        # iterate through checked out repos and import data
        for repo_name, repo_data in checked_out_repos.items():
            repo = repo_data.get("repo")
            for purl in yield_purls_from_yaml_files(repo.working_dir):
                # TODO: use batch create for efficiency
                package = packagedb_models.Package.objects.create(
                    **purl.to_dict()
                )
