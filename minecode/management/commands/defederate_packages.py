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
from minecode.management.commands import VerboseCommand
from packagedb import models as packagedb_models
from packageurl import PackageURL
import saneyaml
from pathlib import Path
from minecode.management import federatedcode
from django.conf import settings
from urllib.parse import urljoin
import requests

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
        working_path = Path("/home/jono/tmp/")

        account_url = f"{settings.FEDERATEDCODE_GIT_ACCOUNT_URL}/"

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_cluster = data_federation.get_cluster("purls")
        debian_data_repositories = data_cluster._data_repositories_by_purl_type.get("deb") or []

        checked_out_repos = {}
        for data_repository in debian_data_repositories:
            repo_name = data_repository.name
            repo_url = urljoin(account_url, repo_name)
            if requests.get(repo_url).ok:
                clone_path = working_path / repo_name
                checked_out_repos[repo_name] = federatedcode.clone_repository(
                    repo_url=repo_url,
                    clone_path=clone_path,
                    logger=print,
                )
            else:
                break

        # iterate through checked out repos and import data
        packages_to_write = []
        for repo_name, repo in checked_out_repos.items():
            for i, purl in enumerate(yield_purls_from_yaml_files(repo.working_dir)):
                if packages_to_write and not i % 5000:
                    packagedb_models.Package.objects.bulk_create(packages_to_write)
                    packages_to_write.clear()
                package = packagedb_models.Package(
                    type=purl.type,
                    namespace=purl.namespace,
                    name=purl.name,
                    version=purl.version,
                    qualifiers=purl.qualifiers,
                    subpath=purl.subpath or "",
                    download_url=f"{purl}"
                )
                packages_to_write.append(package)

        if packages_to_write:
            packagedb_models.Package.objects.bulk_create(packages_to_write)
            packages_to_write.clear()
