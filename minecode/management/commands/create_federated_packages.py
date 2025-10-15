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

import os
from commoncode.fileutils import walk

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

        # Clone data and config repo
        data_repo = federatedcode.clone_repository(
            repo_url=MINECODE_DATA_MAVEN_REPO,
            logger=logger,
        )
        for purl in yield_purls_from_yaml_files(data_repo.working_dir):
            package = packagedb_models.Package.objects.create(
                **purl.to_dict()
            )
