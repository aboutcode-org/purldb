#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from dateutil.parser import parse as dateutil_parse
from os.path import dirname
import logging
import sys

import requests

from minecode.management.commands import VerboseCommand
from minecode.collectors.maven import collect_links_from_text
from minecode.collectors.maven import filter_for_artifacts
from packagedb.models import Package


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = 'Get and set release_date for Maven Packages'

    def handle(self, *args, **options):
        queryset = Package.objects.filter(
            type='maven',
            release_date=None,
            download_url__startswith='https://repo1.maven.org/maven2'
        )
        object_count = queryset.count()
        chunk_size = 2000
        iterator = queryset.iterator(chunk_size=chunk_size)
        unsaved_objects = []

        logger.info(f'Updating release_date for {object_count} packages')
        for index, package in enumerate(iterator, start=1):
            download_url = package.download_url
            package_url = package.package_url
            logger.info(f'Updating release_date for package {package_url} ({download_url})')
            package_version_page_url = dirname(download_url)
            filename = download_url.rsplit('/')[-1]
            response = requests.get(package_version_page_url)
            if response:
                timestamps_by_links = collect_links_from_text(response.text, filter=filter_for_artifacts)
                timestamp = timestamps_by_links.get(filename)
                if not timestamp:
                    logger.info(f'\tCould not get release_date for package {package_url} ({download_url})')
                    continue
                timestamp = dateutil_parse(timestamp)
                package.release_date = timestamp
                unsaved_objects.append(package)
                logger.info(f'\t{package_url} ({download_url}) release_date has been updated to {timestamp}')
            else:
                logger.info(f'\t{package_url} not updated: error encountered when visiting {package_version_page_url}')
            if not (index % chunk_size) and unsaved_objects:
                logger.info(f'{index:,} / {object_count:,} Packages processed')

        logger.info('Updating Package objects...')
        updated_packages_count = Package.objects.bulk_update(
            objs=unsaved_objects,
            fields=['release_date'],
            batch_size=1000,
        )
        logger.info(f'Updated {updated_packages_count} Package objects')
