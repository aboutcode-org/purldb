#
# Copyright (c) 2020 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from datetime import datetime
import logging
import sys
import time

from django.db import transaction

from matchcode.indexing import index_package_archives
from matchcode.indexing import index_package_directories
from matchcode.indexing import index_package_file
from matchcode.management.commands import VerboseCommand
from matchcode.models import get_or_create_indexable_package
from matchcode.models import IndexablePackage
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
        total_indexable_packages_created = 0
        total_indexed_package_archives = 0
        total_indexed_package_files = 0
        total_indexed_adci = 0
        total_indexed_adsi = 0

        logger.setLevel(self.get_verbosity(**options))
        start = time.time()

        packages = Package.objects.filter(sha1__isnull=False)
        for package in packages.iterator():
            with transaction.atomic():
                indexable_package, created_indexable_package = get_or_create_indexable_package(package)
                if created_indexable_package:
                    total_indexable_packages_created += 1
                created_package_archive = index_package_archives(indexable_package)
                if created_package_archive:
                    total_indexed_package_archives += 1

        resources = Resource.objects.filter(sha1__isnull=False)
        for resource in resources.iterator():
            with transaction.atomic():
                created_package_file, created_indexable_package = index_package_file(resource)
                if created_package_file:
                    total_indexed_package_files += 1
                if created_indexable_package:
                    total_indexable_packages_created += 1

        indexable_packages = IndexablePackage.objects.all()
        for indexable_package in indexable_packages.iterator():
            with transaction.atomic():
                indexed_adci, indexed_adsi = index_package_directories(indexable_package)
                total_indexed_adci += indexed_adci
                total_indexed_adsi += indexed_adsi

        # TODO: Format this better for viewing on terminal
        print('Package indexing completed at: {}'.format(datetime.utcnow().isoformat()))
        total_duration = int(time.time() - start)
        print('Total run duration: {} seconds'.format(total_duration))
        print('Created:')
        print('IndexablePackages: {}'.format(total_indexable_packages_created))
        print('ExactPackageArchiveIndex: {}'.format(total_indexed_package_archives))
        print('ExactFileIndex: {}'.format(total_indexed_package_files))
        print('ApproximateDirectoryContentIndex: {}'.format(total_indexed_adci))
        print('ApproximateDirectoryStructureIndex: {}'.format(total_indexed_adsi))
