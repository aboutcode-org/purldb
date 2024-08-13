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
import traceback
from os.path import basename

from django.db import transaction
from django.db.utils import DataError
from django.utils import timezone

from dateutil.parser import parse as dateutil_parse
from packageurl import normalize_qualifiers

from minecode.collectors.maven import MavenNexusCollector
from minecode.management.commands import VerboseCommand
from minecode.models import ProcessingError
from packagedb.models import Package

DEFAULT_TIMEOUT = 30

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def update_packages(packages, fields_to_update):
    try:
        with transaction.atomic():
            Package.objects.bulk_update(objs=packages, fields=fields_to_update)
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
                    message = f"Error updating Package {package.package_uid}:\n\n{traceback_message}"
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
                message = (
                    f"Error creating Package {package.purl}:\n\n{traceback_message}"
                )
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
            "download_url",
            "repository_homepage_url",
            "repository_download_url",
            "api_data_url",
            "release_date",
            "last_modified_date",
            "history",
        ]
        upc = update_packages(unsaved_existing_packages, fields_to_update)
        updated_packages_count += upc
        unsaved_existing_packages = []
        if upc > 0:
            updated = True

    if unsaved_existing_packages_lowercased:
        fields_to_update = [
            "namespace",
            "name",
            "version",
            "qualifiers",
            "download_url",
            "repository_homepage_url",
            "repository_download_url",
            "api_data_url",
            "release_date",
            "last_modified_date",
            "history",
        ]
        upc = update_packages(unsaved_existing_packages_lowercased, fields_to_update)
        updated_packages_count += upc
        unsaved_existing_packages_lowercased = []
        if upc > 0:
            updated = True

    if updated:
        logger.info(f"Updated {updated_packages_count:,} Maven Packages")

    if unsaved_new_packages:
        cpc = create_packages(unsaved_new_packages)
        created_packages_count += cpc
        unsaved_new_packages = []
        if cpc > 0:
            logger.info(f"Created {created_packages_count:,} Maven Packages")

    if packages_to_delete:
        dpc = delete_packages(packages_to_delete)
        packages_to_delete = []
        deleted_packages_count += dpc
        if dpc > 0:
            logger.info(f"Deleted {deleted_packages_count:,} Duplicate Maven Packages")

    return (
        unsaved_existing_packages,
        unsaved_existing_packages_lowercased,
        unsaved_new_packages,
        packages_to_delete,
    )


def update_package_fields(package, maven_package, field_names):
    updated_fields = []
    for field in field_names:
        p_val = getattr(package, field)
        value = getattr(maven_package, field)
        if field == "qualifiers":
            value = normalize_qualifiers(value, encode=True)
        if field == "release_date":
            value = dateutil_parse(value)
        if p_val != value:
            setattr(package, field, value)
            if field == "release_date":
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
            "updated_fields": updated_fields,
        }
        package.append_to_history(
            "Package field values have been updated.",
            data=data,
        )
        logger.debug(f"Updated existing Package {package.package_uid}")
        return package


def update_maven_packages(
    maven_package, fields_to_update, lowercased_purl_fields=False
):
    namespace = maven_package.namespace
    name = maven_package.name
    version = maven_package.version
    normalized_qualifiers = normalize_qualifiers(maven_package.qualifiers, encode=True)

    if lowercased_purl_fields:
        namespace = namespace.lower()
        name = name.lower()
        version = version.lower()
        normalize_qualifiers = normalize_qualifiers.lower()

    existing_packages = Package.objects.filter(
        type="maven",
        namespace=namespace,
        name=name,
        version=version,
        qualifiers=normalized_qualifiers or "",
    )
    if existing_package.exists():
        duplicate_packages = []
        for existing_package in existing_packages:
            if existing_package.download_url != maven_package.download_url:
                logger.debug(
                    f"Deleted duplicate Package with incorrect download URL {existing_package.package_uid}"
                )
                duplicate_packages.append(existing_package)

        duplicate_packages_pks = [p.pk for p in duplicate_packages]
        existing_package = Package.objects.exclude(
            pk__in=duplicate_packages_pks
        ).get_or_none(
            type="maven",
            namespace=namespace,
            name=name,
            version=version,
            qualifiers=normalized_qualifiers or "",
        )
        if existing_package:
            existing_package = update_package_fields(
                existing_package, maven_package, fields_to_update
            )
            return existing_package, duplicate_packages
    else:
        return None, []


class Command(VerboseCommand):
    help = "Update maven Package values"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create_package",
            type=bool,
            help="Create new Maven Packages if it does not exist in our database",
        )

    def handle(self, *args, **options):
        create_package = options.get("create_package", False)
        updated_packages_count = 0
        created_packages_count = 0
        deleted_packages_count = 0
        unsaved_new_packages = []
        unsaved_existing_packages = []
        unsaved_existing_packages_lowercased = []
        packages_to_delete = []

        logger.info("Updating or Adding new Packages from Maven Index")
        collector = MavenNexusCollector()
        for i, maven_package in enumerate(collector.get_packages()):
            if not i % 1000:
                logger.info(f"Processed {i:,} Maven Artifacts")
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

            fields_to_update = [
                "download_url",
                "repository_homepage_url",
                "repository_download_url",
                "api_data_url",
                "release_date",
            ]
            existing_package, duplicate_packages = update_maven_packages(
                maven_package, fields_to_update
            )
            if existing_package:
                unsaved_existing_packages.append(existing_package)
                packages_to_delete.extend(duplicate_packages)
                continue

            fields_to_update = [
                "namespace",
                "name",
                "version",
                "qualifiers",
                "download_url",
                "repository_homepage_url",
                "repository_download_url",
                "api_data_url",
                "release_date",
            ]
            existing_package_lowercased, duplicate_packages = update_maven_packages(
                maven_package, fields_to_update, lowercased_purl_fields=True
            )
            if existing_package_lowercased:
                unsaved_existing_packages_lowercased.append(existing_package_lowercased)
                packages_to_delete.extend(duplicate_packages)
                continue

            if Package.objects.filter(download_url=maven_package.download_url).exists():
                logger.debug(
                    f"Skipping creation of {maven_package.purl} - already exists"
                )
                continue

            if create_package:
                normalized_qualifiers = normalize_qualifiers(
                    maven_package.qualifiers, encode=True
                )
                new_package = Package(
                    type=maven_package.type,
                    namespace=maven_package.namespace,
                    name=maven_package.name,
                    version=maven_package.version,
                    qualifiers=normalized_qualifiers or "",
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
                logger.debug(f"Created Package {maven_package.purl}")

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
