#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys

import requests

from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from packagedcode.maven import get_urls

TIMEOUT = 10

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def check_download_url(download_url):
    response = requests.get(download_url, timeout=TIMEOUT)
    return response.ok


class Command(VerboseCommand):
    help = 'Update maven Package download_url values'

    def handle(self, *args, **options):
        maven_packages = Package.objects.filter(type='maven')
        maven_packages_count = maven_packages.count()
        logger.info(f'Checking {maven_packages_count:,} Maven Package download URLs')
        packages_to_delete = []
        unsaved_packages = []
        for package in maven_packages:
            # If the package's download URL is not valid, then we update it
            if not check_download_url(package.download_url):
                urls = get_urls(
                    namespace=package.namespace,
                    name=package.name,
                    version=package.version,
                    qualifiers=package.qualifiers,
                )
                generated_download_url = urls['repository_download_url']
                if Package.objects.filter(download_url=generated_download_url).exists():
                    # This download url already exists in the database, we should just remove this record.
                    packages_to_delete.append(package)
                elif check_download_url(generated_download_url):
                    package.download_url = generated_download_url
                    unsaved_packages.append(package)
                    logger.info(f'Updated download_url for {package.package_uid}')
                else:
                    logger.info(f'Error: cannot generate a valid download_url for package {package.package_uid}')

        if unsaved_packages:
            Package.objects.bulk_update(
                objs=unsaved_packages,
                fields=[
                    'download_url',
                ]
            )
            logger.info(f'Updated {unsaved_packages.count():,} Maven Packages')

        if packages_to_delete:
            pks = [p.pk for p in packages_to_delete]
            Package.objects.filter(pk__in=pks).delete()
            logger.info(f'Deleted {pks.count():,} Maven Package duplicates')
