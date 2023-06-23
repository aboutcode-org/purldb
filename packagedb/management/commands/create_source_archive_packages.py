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
from packagedb.management.commands import VerboseCommand
from packagedb.models import Package
from packagedb.models import PackageContentType


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
        reportable = {
            'purl': purl,
            'source_download_url': source_download_url,
            'source_type': source_type,
            'source_namespace': source_namespace,
            'source_name': source_name,
            'source_version': source_version,
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
        rows = get_rows(wb, 'PACKAGES')

        for row in rows:
            # Look up the package the row is for by using the purl to query the db.
            purl = row['purl']
            lookups = purl_to_lookups(purl)
            packages = Package.objects.filter(**lookups)

            # Get the binary package
            # We use .get(qualifiers="") because the binary maven JAR has no qualifiers
            binary_package = packages.get(qualifiers='')

            package_set = binary_package.package_set
            if not package_set.package_set:
                # Create a new UUID and set it as this set of packages package_set value
                package_set = uuid4()

            # Set package_content value for binary_package, if needed
            if not binary_package.package_content:
                binary_package.package_content = PackageContentType.BINARY

            # Get the source package
            # We use .get(qualifiers__contains='classifier=sources') as source JARs have the qualifiers set
            source_package = packages.get(qualifiers__contains='classifier=sources')

            # Set the package_set value to be the same as the one used for binary_package, if needed
            if not source_package.package_set:
                source_package.package_set = package_set

            # Set source_package value for binary_package, if needed
            if not source_package.package_content:
                source_package.package_content = PackageContentType.SOURCE_ARCHIVE

            # Create new Package from the source_ fields
            package = Package.objects.create(
                type=row['source_type'],
                namespace=row['source_namespace'],
                name=row['source_name'],
                version=row['source_version'],
                download_url=row['source_download_url'],
                package_set=package_set,
                # TODO: Should package_content be SOURCE_ARCHIVE or SOURCE_REPO?
                package_content=PackageContentType.SOURCE_ARCHIVE,
            )
            if package:
                add_package_to_scan_queue(package)
