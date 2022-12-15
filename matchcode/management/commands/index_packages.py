#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import datetime
import logging
import sys
import time

from django.db import transaction

from discovery.management.commands import VerboseCommand
from matchcode.indexing import index_package_archives
from matchcode.indexing import index_package_directories
from matchcode.indexing import index_package_file
from packagedb.models import Package
from packagedb.models import Resource


TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(VerboseCommand):
    help = 'Index all Package SHA1 from PackageDB.'

    def handle(self, *args, **options):
        # Stats to keep track of during indexing
        total_indexed_package_archives = 0
        total_indexed_package_files = 0
        total_indexed_adci = 0
        total_indexed_adsi = 0

        logger.setLevel(self.get_verbosity(**options))
        start = time.time()

        packages = Package.objects.filter(sha1__isnull=False)
        for package in packages.iterator():
            with transaction.atomic():
                created_package_archive = index_package_archives(package)
                if created_package_archive:
                    total_indexed_package_archives += 1

        resources = Resource.objects.filter(sha1__isnull=False)
        for resource in resources.iterator():
            with transaction.atomic():
                created_package_file = index_package_file(resource)
                if created_package_file:
                    total_indexed_package_files += 1

        for package in Package.objects.all().iterator():
            with transaction.atomic():
                indexed_adci, indexed_adsi = index_package_directories(package)
                total_indexed_adci += indexed_adci
                total_indexed_adsi += indexed_adsi

        # TODO: Format this better for viewing on terminal
        print('Package indexing completed at: {}'.format(datetime.utcnow().isoformat()))
        total_duration = int(time.time() - start)
        print('Total run duration: {} seconds'.format(total_duration))
        print('Created:')
        print('ExactPackageArchiveIndex: {}'.format(total_indexed_package_archives))
        print('ExactFileIndex: {}'.format(total_indexed_package_files))
        print('ApproximateDirectoryContentIndex: {}'.format(total_indexed_adci))
        print('ApproximateDirectoryStructureIndex: {}'.format(total_indexed_adsi))
