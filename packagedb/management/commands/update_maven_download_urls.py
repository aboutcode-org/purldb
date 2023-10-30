#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import copy
import logging
import sys

from django.db import transaction

from urllib3.util import Retry
from requests import Session
from requests.adapters import HTTPAdapter
import requests

from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from packagedcode.maven import get_urls
from packageurl import PackageURL

DEFAULT_TIMEOUT = 30

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

session = Session()
session.mount('https://', HTTPAdapter(max_retries=Retry(10)))


# This is from https://stackoverflow.com/questions/4856882/limiting-memory-use-in-a-large-django-queryset/5188179#5188179
class MemorySavingQuerysetIterator(object):
    def __init__(self,queryset,max_obj_num=1000):
        self._base_queryset = queryset
        self._generator = self._setup()
        self.max_obj_num = max_obj_num

    def _setup(self):
        for i in range(0,self._base_queryset.count(),self.max_obj_num):
            # By making a copy of of the queryset and using that to actually access
            # the objects we ensure that there are only `max_obj_num` objects in
            # memory at any given time
            smaller_queryset = copy.deepcopy(self._base_queryset)[i:i+self.max_obj_num]
            logger.debug('Grabbing next %s objects from DB' % self.max_obj_num)
            for obj in smaller_queryset.iterator():
                yield obj

    def __iter__(self):
        return self._generator

    def next(self):
        return self._generator.next()


def check_download_url(url, timeout=DEFAULT_TIMEOUT):
    """Return True if `url` is resolvable and accessable"""
    if not url:
        return
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.ok
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"[Exception] {exception}")
        return False


class Command(VerboseCommand):
    help = 'Update maven Package download_url values'

    def handle(self, *args, **options):
        maven_packages = Package.objects.filter(type='maven')
        maven_packages_count = maven_packages.count()
        logger.info(f'Checking {maven_packages_count:,} Maven Package download URLs')
        packages_to_delete = []
        unsaved_packages = []
        processed_packages_count = 0
        for i, package in enumerate(MemorySavingQuerysetIterator(maven_packages)):
            if not i % 1000:
                logger.info(f'Checked {i:,} / {maven_packages_count:,} Maven Package download URLs')
            if not i % 2000 and unsaved_packages:
                with transaction.atomic():
                    Package.objects.bulk_update(
                        objs=unsaved_packages,
                        fields=[
                            'download_url',
                        ]
                    )
                processed_packages_count += unsaved_packages.count()
                unsaved_packages = []
                logger.info(f'Updated {processed_packages_count:,} Maven Packages')
            # If the package's download URL is not valid, then we update it
            if not check_download_url(package.download_url):
                package_url = PackageURL(
                    type=package.type,
                    namespace=package.namespace,
                    name=package.name,
                    version=package.version,
                    qualifiers=package.qualifiers,
                )
                urls = get_urls(
                    namespace=package_url.namespace,
                    name=package_url.name,
                    version=package_url.version,
                    qualifiers=package_url.qualifiers,
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
            with transaction.atomic():
                Package.objects.bulk_update(
                    objs=unsaved_packages,
                    fields=[
                        'download_url',
                    ]
                )
            processed_packages_count += unsaved_packages.count()
            unsaved_packages = []
            logger.info(f'Updated {processed_packages_count:,} Maven Packages')

        if packages_to_delete:
            pks = [p.pk for p in packages_to_delete]
            with transaction.atomic():
                Package.objects.filter(pk__in=pks).delete()
            logger.info(f'Deleted {pks.count():,} Maven Package duplicates')