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

import openpyxl

from minecode.management.commands import VerboseCommand
from minecode.model_utils import add_package_to_scan_queue
from packagedb.models import Package
from packagedb.models import PackageContentType
from purl2vcs.find_source_repo import add_source_package_to_package_set
from purl2vcs.find_source_repo import get_package_object_from_purl

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def get_rows(workbook, sheet_name):
    try:
        inventory_sheet = workbook[sheet_name]
    except KeyError:
        return dict()
    inventory_column_indices = {
        cell.value.lower(): i for i, cell in enumerate(inventory_sheet[1]) if cell.value
    }
    rows = []
    for row in inventory_sheet.iter_rows(min_row=2):
        purl = row[inventory_column_indices["purl"]].value
        source_download_url = row[inventory_column_indices["source_download_url"]].value
        source_type = row[inventory_column_indices["source_type"]].value
        source_namespace = row[inventory_column_indices["source_namespace"]].value
        source_name = row[inventory_column_indices["source_name"]].value
        source_version = row[inventory_column_indices["source_version"]].value
        source_purl = row[inventory_column_indices["source_purl"]].value
        reportable = {
            "purl": purl,
            "source_download_url": source_download_url,
            "source_type": source_type,
            "source_namespace": source_namespace,
            "source_name": source_name,
            "source_version": source_version,
            "source_purl": source_purl,
        }
        rows.append(reportable)
    return rows


class Command(VerboseCommand):
    help = "Create source archive packages for related"

    def add_arguments(self, parser):
        parser.add_argument("--input", type=str)

    def handle(self, *args, **options):
        input = options.get("input")
        if not input:
            return

        # Collect resource info
        wb = openpyxl.load_workbook(input, read_only=True)
        rows = get_rows(wb, "PACKAGES WITH SOURCES")

        for row in rows:
            # Look up the package the row is for by using the purl to query the db.
            purl = row["purl"]
            print(f"Processing packages for: {purl}")
            package = get_package_object_from_purl(package_url=purl)
            if not package:
                print(f"\t{purl} does not exist in this database. Continuing.")
                continue

            source_package, _created = Package.objects.get_or_create(
                type=row["source_type"],
                namespace=row["source_namespace"],
                name=row["source_name"],
                version=row["source_version"],
                download_url=row["source_download_url"],
                package_content=PackageContentType.SOURCE_REPO,
            )

            if _created:
                add_package_to_scan_queue(source_package)

            package_set_ids = set(package.package_sets.all().values("uuid"))
            source_package_set_ids = set(
                source_package.package_sets.all().values("uuid")
            )

            # If the package exists and already in the set then there is nothing left to do
            if package_set_ids.intersection(source_package_set_ids):
                continue

            add_source_package_to_package_set(
                source_package=source_package,
                package=package,
            )
