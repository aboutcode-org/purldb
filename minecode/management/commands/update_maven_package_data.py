#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from dateutil.parser import parse as dateutil_parse
from os.path import basename
import copy
import logging
import sys
import traceback

from django.db import transaction
from django.db.utils import DataError
from django.utils import timezone

from urllib3.util import Retry
from requests import Session
from requests.adapters import HTTPAdapter
import requests

from minecode.models import ProcessingError
from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from packageurl import normalize_qualifiers
from minecode.collectors.maven import MavenNexusCollector

DEFAULT_TIMEOUT = 30

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

session = Session()
session.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
}
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


def update_packages(packages, fields_to_update):
    try:
        with transaction.atomic():
            Package.objects.bulk_update(
                objs=packages,
                fields=fields_to_update
            )
        updated_packages_count = len(packages)
    except DataError:
        updated_packages_count = 0
        with transaction.atomic():
            # Update each record individually and then try to catch the package causing problems
            for package in packages:
                try:
                    package.save()
                    updated_packages_count += 1
                except DataError:
                    service = basename(__file__)
                    traceback_message = traceback.format_exc()
                    message = f'Error updating Package {package.package_uid}:\n\n{traceback_message}'
                    ProcessingError.objects.create(
                        service=service,
                        date=timezone.now(),
                        error_message=message,
                    )
                    logger.error(message)
    finally:
        return updated_packages_count


def create_packages(packages):
    try:
        with transaction.atomic():
            Package.objects.bulk_create(packages)
        created_packages_count = len(packages)
    except DataError:
        created_packages_count = 0
        for package in packages:
            try:
                package.save()
                created_packages_count += 1
            except DataError:
                service = basename(__file__)
                traceback_message = traceback.format_exc()
                message = f'Error creating Package {package.purl}:\n\n{traceback_message}'
                ProcessingError.objects.create(
                    service=service,
                    date=timezone.now(),
                    error_message=message,
                )
                logger.error(message)
    finally:
        return created_packages_count


def delete_packages(packages):
    package_pks_to_delete = [p.pk for p in packages]
    Package.objects.filter(pk__in=package_pks_to_delete).delete()
    deleted_packages_count = len(packages)
    return deleted_packages_count


def process_packages(
    unsaved_existing_packages,
    unsaved_existing_packages_lowercased,
    unsaved_new_packages,
    packages_to_delete,
    updated_packages_count,
    created_packages_count,
    deleted_packages_count,
):
    updated = False
    if unsaved_existing_packages:
        fields_to_update = [
            'download_url',
            'repository_homepage_url',
            'repository_download_url',
            'api_data_url',
            'release_date',
            'last_modified_date',
            'history',
        ]
        upc = update_packages(unsaved_existing_packages, fields_to_update)
        updated_packages_count += upc
        unsaved_existing_packages = []
        if upc > 0:
            updated = True

    if unsaved_existing_packages_lowercased:
        fields_to_update=[
            'namespace',
            'name',
            'version',
            'qualifiers',
            'download_url',
            'repository_homepage_url',
            'repository_download_url',
            'api_data_url',
            'release_date',
            'last_modified_date',
            'history',
        ]
        upc = update_packages(unsaved_existing_packages_lowercased, fields_to_update)
        updated_packages_count += upc
        unsaved_existing_packages_lowercased = []
        if upc > 0:
            updated = True

    if updated:
        logger.info(f'Updated {updated_packages_count:,} Maven Packages')

    if unsaved_new_packages:
        cpc = create_packages(unsaved_new_packages)
        created_packages_count += cpc
        unsaved_new_packages = []
        if cpc > 0:
            logger.info(f'Created {created_packages_count:,} Maven Packages')

    if packages_to_delete:
        dpc = delete_packages(packages_to_delete)
        packages_to_delete = []
        deleted_packages_count += dpc
        if dpc > 0:
            logger.info(f'Deleted {deleted_packages_count:,} Duplicate Maven Packages')

    return unsaved_existing_packages, unsaved_existing_packages_lowercased, unsaved_new_packages, packages_to_delete


def update_package_fields(package, maven_package, field_names):
    updated_fields = []
    for field in field_names:
        p_val = getattr(package, field)
        value = getattr(maven_package, field)
        if field == 'qualifiers':
            value = normalize_qualifiers(value, encode=True)
        if field == 'release_date':
            value = dateutil_parse(value)
        if p_val != value:
            setattr(package, field, value)
            if field == 'release_date':
                p_val = str(p_val)
                value = str(value)
            entry = dict(
                field=field,
                old_value=p_val,
                new_value=value,
            )
            updated_fields.append(entry)

    if updated_fields:
        data = {
            'updated_fields': updated_fields,
        }
        package.append_to_history(
            'Package field values have been updated.',
            data=data,
        )
        logger.debug(f'Updated existing Package {package.package_uid}')
        return package


class Command(VerboseCommand):
    help = 'Update maven Package values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create_package',
            type=bool,
            help='Create new Maven Packages if it does not exist in our database'
        )

    def handle(self, *args, **options):
        create_package = options.get('create_package', False)
        updated_packages_count = 0
        created_packages_count = 0
        deleted_packages_count = 0
        logger.info('Updating or Adding new Packages from Maven Index')
        collector = MavenNexusCollector()
        unsaved_new_packages = []
        unsaved_existing_packages = []
        unsaved_existing_packages_lowercased = []
        packages_to_delete = []
        for i, maven_package in enumerate(collector.get_packages()):
            if not i % 1000:
                logger.info(f'Processed {i:,} Maven Artifacts')
            if not i % 2000:
                (
                    unsaved_existing_packages,
                    unsaved_existing_packages_lowercased,
                    unsaved_new_packages,
                    packages_to_delete,
                    updated_packages_count,
                    created_packages_count,
                    deleted_packages_count,
                ) = process_packages(
                    unsaved_existing_packages=unsaved_existing_packages,
                    unsaved_existing_packages_lowercased=unsaved_existing_packages_lowercased,
                    unsaved_new_packages=unsaved_new_packages,
                    packages_to_delete=packages_to_delete,
                    updated_packages_count=updated_packages_count,
                    created_packages_count=created_packages_count,
                    deleted_packages_count=deleted_packages_count,
                )

            normalized_qualifiers = normalize_qualifiers(maven_package.qualifiers, encode=True)
            existing_packages = Package.objects.filter(
                type='maven',
                namespace=maven_package.namespace,
                name=maven_package.name,
                version=maven_package.version,
                qualifiers=normalized_qualifiers or ''
            )

            duplicate_packages = []
            for existing_package in existing_packages:
                if existing_package.download_url != maven_package.download_url:
                    logger.debug(f'Deleted duplicate Package with incorrect download URL {existing_package.package_uid}')
                    packages_to_delete.append(existing_package)
                    duplicate_packages.append(existing_package)

            duplicate_packages_pks = [p.pk for p in duplicate_packages]
            existing_package = Package.objects.exclude(
                pk__in=duplicate_packages_pks
            ).get_or_none(
                type='maven',
                namespace=maven_package.namespace,
                name=maven_package.name,
                version=maven_package.version,
                qualifiers=normalized_qualifiers or ''
            )
            if existing_package:
                fields_to_update = [
                    'download_url',
                    'repository_homepage_url',
                    'repository_download_url',
                    'api_data_url',
                    'release_date',
                ]
                existing_package = update_package_fields(
                    existing_package,
                    maven_package,
                    fields_to_update
                )
                unsaved_existing_packages.append(existing_package)
                continue

            if normalized_qualifiers:
                normalized_qualifiers = normalized_qualifiers.lower()

            existing_packages_lowercased = Package.objects.filter(
                type='maven',
                namespace=maven_package.namespace.lower(),
                name=maven_package.name.lower(),
                version=maven_package.version.lower(),
                qualifiers=normalized_qualifiers or ''
            )

            duplicate_packages_lowercased = []
            for existing_package_lowercased in existing_packages_lowercased:
                if existing_package_lowercased.download_url != maven_package.download_url:
                    logger.debug(f'Deleted duplicate Package with incorrect download URL {existing_package_lowercased.package_uid}')
                    packages_to_delete.append(existing_package_lowercased)
                    duplicate_packages_lowercased.append(existing_package_lowercased)

            duplicate_packages_lowercased_pks = [p.pk for p in duplicate_packages_lowercased]
            existing_package_lowercased = Package.objects.exclude(
                pk__in=duplicate_packages_lowercased_pks
            ).get_or_none(
                type='maven',
                namespace=maven_package.namespace.lower(),
                name=maven_package.name.lower(),
                version=maven_package.version.lower(),
                qualifiers=normalized_qualifiers or ''
            )
            if existing_package_lowercased:
                fields_to_update = [
                    'namespace',
                    'name',
                    'version',
                    'qualifiers',
                    'download_url',
                    'repository_homepage_url',
                    'repository_download_url',
                    'api_data_url',
                    'release_date',
                ]
                existing_package_lowercased = update_package_fields(
                    existing_package_lowercased,
                    maven_package,
                    fields_to_update
                )
                unsaved_existing_packages_lowercased.append(existing_package_lowercased)
                continue

            if Package.objects.filter(download_url=maven_package.download_url).exists():
                logger.debug(f'Skipping creation of {maven_package.purl} - already exists')
                continue

            if create_package:
                new_package = Package(
                    type=maven_package.type,
                    namespace=maven_package.namespace,
                    name=maven_package.name,
                    version=maven_package.version,
                    qualifiers=normalized_qualifiers or '',
                    download_url=maven_package.download_url,
                    size=maven_package.size,
                    sha1=maven_package.sha1,
                    release_date=dateutil_parse(maven_package.release_date),
                    repository_homepage_url=maven_package.repository_homepage_url,
                    repository_download_url=maven_package.repository_download_url,
                    api_data_url=maven_package.api_data_url,
                )
                new_package.created_date = timezone.now()
                unsaved_new_packages.append(new_package)
                logger.debug(f'Created Package {maven_package.purl}')

        (
            unsaved_existing_packages,
            unsaved_existing_packages_lowercased,
            unsaved_new_packages,
            packages_to_delete,
            updated_packages_count,
            created_packages_count,
            deleted_packages_count,
        ) = process_packages(
            unsaved_existing_packages=unsaved_existing_packages,
            unsaved_existing_packages_lowercased=unsaved_existing_packages_lowercased,
            unsaved_new_packages=unsaved_new_packages,
            packages_to_delete=packages_to_delete,
            updated_packages_count=updated_packages_count,
            created_packages_count=created_packages_count,
            deleted_packages_count=deleted_packages_count,
        )
