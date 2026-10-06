#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

from django.conf import settings

import requests
import saneyaml
import json

from aboutcode.federated import DataFederation
from commoncode import fileutils
from minecode.management import federatedcode
from minecode.management.commands import VerboseCommand
from minecode.management.commands import federate_packages
from packagedb import models as packagedb_models
from packageurl import PackageURL
from packageurl.contrib import purl2url

"""
Utility command to find license oddities.
"""
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


def yield_purl_strs_from_yaml_files(location):
    for root, _, files in fileutils.walk(location):
        if "purls.yml" not in files:
            continue
        for file in files:
            fp = os.path.join(root, file)
            with open(fp) as f:
                purl_strs = saneyaml.load(f.read()) or []
            yield from purl_strs


def yield_package_data_from_json(location):
    for root, _, files in fileutils.walk(location):
        if "package_data.json" not in files:
            continue
        for file in files:
            fp = os.path.join(root, file)
            with open(fp) as f:
                package_data = json.load(f)
            yield package_data


class Command(VerboseCommand):
    help = "Create Packages from FederatedCode repos"

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
            help="Type of package to be defederated",
        )
        parser.add_argument(
            "--datakind",
            type=str,
            required=True,
            action="append",
            help="Kind of package data to be defederated",
        )

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        working_dir = options.get("working_directory")
        if working_dir:
            working_path = Path(working_dir)
        else:
            working_path = Path(fileutils.get_temp_dir())

        account_url = f"{settings.FEDERATEDCODE_GIT_ACCOUNT_URL}/"

        package_types = options.get("package_type") or []
        datakinds = options.get("datakind") or []
        federate_packages.validate_datakind_options(datakinds)

        # Clone data and config repo
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        data_clusters = [data_federation.get_cluster(datakind) for datakind in datakinds]

        checked_out_repos = {}
        for data_cluster in data_clusters:
            for package_type in package_types:
                data_repositories = (
                    data_cluster._data_repositories_by_purl_type.get(package_type) or []
                )
                if not data_repositories:
                    logger.info(f"no data repositories for package type {package_type}")
                    continue

                for data_repository in data_repositories:
                    repo_name = data_repository.name
                    repo_url = urljoin(account_url, repo_name)
                    if requests.get(repo_url).ok:
                        clone_path = working_path / package_type / repo_name
                        checked_out_repos[repo_name] = federatedcode.clone_repository(
                            repo_url=repo_url,
                            clone_path=clone_path,
                            logger=logger.info,
                        )
                    else:
                        break

                # iterate through checked out repos and import data
                packages_to_write = []
                for repo_name, repo in checked_out_repos.items():
                    # TODO: refactor
                    logger.info(f"Creating Packages from {repo_name}")
                    if data_cluster.data_kind == "purls":
                        for i, purl_str in enumerate(
                            yield_purl_strs_from_yaml_files(repo.working_dir), start=1
                        ):
                            purl = PackageURL.from_string(purl_str)
                            if packages_to_write and not i % 5000:
                                packagedb_models.Package.objects.bulk_create(packages_to_write)
                                logger.info(f"Created {i} Packages from {repo_name}")
                                packages_to_write.clear()
                            package = packagedb_models.Package(
                                type=purl.type,
                                namespace=purl.namespace,
                                name=purl.name,
                                version=purl.version,
                                qualifiers=purl.qualifiers,
                                subpath=purl.subpath or "",
                                download_url=purl2url.get_download_url(purl_str),
                                repository_download_url=purl2url.get_repo_download_url(purl_str),
                            )
                            packages_to_write.append(package)
                    elif data_cluster.data_kind == "package_data":
                        # TODO: populate all data from jsons
                        for package_data in yield_package_data_from_json(repo.working_dir):
                            purl_str = package_data["purl"]
                            purl = PackageURL.from_string(purl_str)
                            if packages_to_write and not i % 5000:
                                packagedb_models.Package.objects.bulk_create(packages_to_write)
                                logger.info(f"Created {i} Packages from {repo_name}")
                                packages_to_write.clear()
                            package = packagedb_models.Package(
                                type=purl.type,
                                namespace=purl.namespace,
                                name=purl.name,
                                version=purl.version,
                                qualifiers=purl.qualifiers,
                                subpath=purl.subpath or "",
                                download_url=purl2url.get_download_url(purl_str),
                                repository_download_url=purl2url.get_repo_download_url(purl_str),
                            )
                            packages_to_write.append(package)

                if packages_to_write:
                    packagedb_models.Package.objects.bulk_create(packages_to_write)
                    logger.info(f"Created {i} Packages from {repo_name}")
                    packages_to_write.clear()

                # clean up
                package_type_clone_path = working_path / package_type
                fileutils.delete(package_type_clone_path)
                checked_out_repos.clear()
