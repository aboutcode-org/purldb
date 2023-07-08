#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from uuid import uuid4
import logging
import sys

from packageurl.contrib.django.utils import purl_to_lookups
import openpyxl

from minecode.model_utils import add_package_to_scan_queue
from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet


TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def get_rows(workbook, sheet_name):
    try:
        inventory_sheet = workbook[sheet_name]
    except KeyError:
        return dict()
    inventory_column_indices = {cell.value.lower(): i for i, cell in enumerate(inventory_sheet[1]) if cell.value}
    rows = []
    for row in inventory_sheet.iter_rows(min_row=2):
        purl = row[inventory_column_indices['purl']].value
        source_download_url = row[inventory_column_indices['source_download_url']].value
        source_type = row[inventory_column_indices['source_type']].value
        source_namespace = row[inventory_column_indices['source_namespace']].value
        source_name = row[inventory_column_indices['source_name']].value
        source_version = row[inventory_column_indices['source_version']].value
        source_purl = row[inventory_column_indices['source_purl']].value
        source_subpath = row[inventory_column_indices['source_subpath']].value
        reportable = {
            'purl': purl,
            'source_download_url': source_download_url,
            'source_type': source_type,
            'source_namespace': source_namespace,
            'source_name': source_name,
            'source_version': source_version,
            'source_purl': source_purl,
            'source_subpath': source_subpath,
        }
        rows.append(reportable)
    return rows


class Command(VerboseCommand):
    help = 'Create source archive packages for related'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str)

    def handle(self, *args, **options):
        input = options.get('input')
        if not input:
            return

        # Collect resource info
        wb = openpyxl.load_workbook(input, read_only=True)
        rows = get_rows(wb, 'PACKAGES WITH SOURCES')

        for row in rows:
            # Look up the package the row is for by using the purl to query the db.
            purl = row['purl']
            source_purl = row['source_purl']
            print(f'Processing packages for: {purl}')

            lookups = purl_to_lookups(purl)
            packages = Package.objects.filter(**lookups)

            # Get the binary package
            # We use .get(qualifiers="") because the binary maven JAR has no qualifiers
            binary_package = packages.get_or_none(qualifiers='')
            if not binary_package:
                print(f'\t{purl} does not exist in this database. Continuing.')
                continue

            # binary packages can only be part of one package set
            package_set = binary_package.package_sets.first()

            # Create new Package from the source_ fields
            source_repo_package, created = Package.objects.get_or_create(
                type=row['source_type'],
                namespace=row['source_namespace'],
                name=row['source_name'],
                version=row['source_version'],
                subpath=row['source_subpath'],
                download_url=row['source_download_url'],
                package_content=PackageContentType.SOURCE_REPO,
            )
            package_set.add_to_package_set(source_repo_package)
            if created:
                add_package_to_scan_queue(source_repo_package)
                print(f'\tCreated source repo package {source_purl} for {purl}')
            else:
                print(f'\tAssigned source repo package {source_purl} to Package set {package_set.uuid}')
