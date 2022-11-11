#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import signal
import sys
import time

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from commoncode import fileutils
from packagedcode import get_package_handler
from packagedcode import UnknownPackageDatasource
from packagedcode.models import PackageData
from packageurl import normalize_qualifiers

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from discovery import mappers  # NOQA
from discovery import visitors  # NOQA

from discovery import map_router
from discovery.models import ResourceURI
from packagedb.models import DependentPackage
from packagedb.models import Package
from packagedb.models import Party
from discovery.management.commands import get_error_message
from discovery.management.commands import VerboseCommand
from discovery.models import ScannableURI
from discovery.utils import stringify_null_purl_fields


TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 10

MUST_STOP = False


def stop_handler(*args, **kwargs):
    """
    Signal handler to set global variable to True.
    """
    global MUST_STOP
    MUST_STOP = True


signal.signal(signal.SIGTERM, stop_handler)

# number of mappable ResourceURI processed at once
MAP_BATCH_SIZE = 10


class Command(VerboseCommand):
    help = 'Run a mapping worker.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exit-on-empty',
            dest='exit_on_empty',
            default=False,
            action='store_true',
            help='Do not loop forever. Exit when the queue is empty.')

    def handle(self, *args, **options):
        """
        Get the next available candidate ResourceURI and start the processing.
        Loops forever and sleeps a short while if there are no ResourceURI left to map.
        """
        global MUST_STOP

        logger.setLevel(self.get_verbosity(**options))
        exit_on_empty = options.get('exit_on_empty')

        sleeping = False

        while True:
            if MUST_STOP:
                logger.info('Graceful exit of the map loop.')
                break

            mappables = ResourceURI.objects.get_mappables()[:MAP_BATCH_SIZE]

            if not mappables:
                if exit_on_empty:
                    logger.info('No mappable resource, exiting...')
                    break

                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    logger.info('No mappable resource, sleeping...')

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            sleeping = False

            for resource_uri in mappables:
                logger.info('Mapping {}'.format(resource_uri))
                map_uri(resource_uri)


def map_uri(resource_uri, _map_router=map_router):
    """
    Call a mapper for a ResourceURI.
    `_map_router` is the Router to use for routing. Used for tests only.
    """
    # FIXME: returning a string or sequence is UGLY
    try:
        mapped_scanned_packages = _map_router.process(
            resource_uri.uri, resource_uri=resource_uri)

        logger.debug('map_uri: Package URI: {}'.format(resource_uri.uri))

        # consume generators
        mapped_scanned_packages = mapped_scanned_packages and list(
            mapped_scanned_packages)

        if not mapped_scanned_packages:
            msg = 'No visited scanned packages returned.'
            logger.error(msg)
            resource_uri.last_map_date = timezone.now()
            resource_uri.map_error = msg
            resource_uri.save()
            return

    except Exception as e:
        msg = 'Error: Failed to map while processing ResourceURI: {}\n'.format(
            repr(resource_uri))
        msg += get_error_message(e)
        logger.error(msg)
        # we had an error, so mapped_scanned_packages is an error string
        resource_uri.last_map_date = timezone.now()
        resource_uri.map_error = msg
        resource_uri.save()
        return

    # if we reached this place, we have mapped_scanned_packages that contains
    # packages in ScanCode models format that these are ready to save to the DB

    map_error = ''

    try:
        with transaction.atomic():
            # iterate the ScanCode Package objects returned by the mapper
            # and either save these as new packagedb.Packages or update and
            # existing one

            for scanned_package in mapped_scanned_packages:

                if not isinstance(scanned_package, PackageData):
                    msg = 'Not a ScanCode PackageData type:' + repr(scanned_package)
                    map_error += msg + '\n'
                    logger.error(msg)
                    raise RuntimeError(msg)

                try:
                    handler = get_package_handler(scanned_package)
                    scanned_package.license_expression = handler.compute_normalized_license(scanned_package)
                except UnknownPackageDatasource:
                    # TODO: Should we report an error if we can't compute a normalized license?
                    pass

                if not scanned_package.download_url:
                    # TODO: there could be valid cases where we have no download URL
                    # and still want to create a package???
                    msg = 'No download_url for package:' + repr(scanned_package)
                    map_error += msg + '\n'
                    logger.error(msg)
                    continue

                package_uri = scanned_package.download_url

                logger.debug('Package URI: {}'.format(package_uri))

                visit_level = resource_uri.mining_level

                stored_package = None
                # Check if we already have an existing PackageDB record to update
                # TODO: for now this is done using the package_uri only and
                # we need to refine this to also (or only) use the package_url
                try:
                    # FIXME: also consider the Package URL fields!!!
                    stored_package = Package.objects.get(download_url=package_uri)
                except ObjectDoesNotExist:
                    pass

                if stored_package:
                    # Here we have a pre-existing package that we are updating.
                    # Based on the mining levels, we replace or merge fields
                    # differently

                    existing_level = stored_package.mining_level

                    if visit_level < existing_level:
                        # if the level of the new visit is lower than the level
                        # of the current package, then existing package data
                        # wins and is more important. Its attributes can only be
                        # updated if there was a null values and there is a non-
                        # null values in the new package data from the visit.
                        merge_packages(
                            existing_package=stored_package,
                            new_package_data=scanned_package.to_dict(),
                            replace=False)
                        stored_package.append_to_history('Existing Package values retained due to ResourceURI mining level via map_uri().')
                        # for a foreign key, such as dependencies and parties, we will adopt the
                        # same logic. In this case, parties or dependencies coming from a scanned
                        # package are only added if there is no parties or dependencies in the
                        # existing stored package
                    else:
                        # if the level of the new visit is higher or equal to
                        # the level of the existing package, then new package
                        # data from the visit is more important and wins and its
                        # non-null values replace the values of the existing
                        # package which is updated in the DB.
                        merge_packages(
                            existing_package=stored_package,
                            new_package_data=scanned_package.to_dict(),
                            replace=True)
                        stored_package.append_to_history('Existing Package values replaced due to ResourceURI mining level via map_uri().')
                        # for a foreign key, such as dependencies and parties, we will adopt the
                        # same logic. In this case, parties or dependencies coming from a scanned
                        # package will override existing values. If there are parties in the scanned
                        # package and the existing package, the existing package parties should be
                        # deleted first and then the new package's parties added.

                        stored_package.mining_level = visit_level

                    stored_package.last_modified_date = timezone.now()
                    stored_package.save()
                    logger.debug(' + Updated package\t: {}'.format(package_uri))

                else:
                    # Here a pre-existing packagedb record does not exist
                    # We create a new one from scratch

                    package_data = dict(
                        # FIXME: we should get the file_name in the
                        # PackageData object instead.
                        filename=fileutils.file_name(package_uri),
                        # TODO: update the PackageDB model
                        release_date=scanned_package.release_date,
                        mining_level=visit_level,
                        type=scanned_package.type,
                        namespace=scanned_package.namespace,
                        name=scanned_package.name,
                        version=scanned_package.version,
                        qualifiers=normalize_qualifiers(scanned_package.qualifiers, encode=True),
                        subpath=scanned_package.subpath,
                        primary_language=scanned_package.primary_language,
                        description=scanned_package.description,
                        keywords=scanned_package.keywords,
                        homepage_url=scanned_package.homepage_url,
                        download_url=scanned_package.download_url,
                        size=scanned_package.size,
                        sha1=scanned_package.sha1,
                        md5=scanned_package.md5,
                        sha256=scanned_package.sha256,
                        sha512=scanned_package.sha512,
                        bug_tracking_url=scanned_package.bug_tracking_url,
                        code_view_url=scanned_package.code_view_url,
                        vcs_url=scanned_package.vcs_url,
                        copyright=scanned_package.copyright,
                        license_expression=scanned_package.license_expression,
                        declared_license=scanned_package.declared_license,
                        notice_text=scanned_package.notice_text,
                        source_packages=scanned_package.source_packages
                    )

                    stringify_null_purl_fields(package_data)

                    created_package = Package.objects.create(**package_data)
                    created_package.append_to_history('New Package created from ResourceURI: {} via map_uri().'.format(resource_uri))

                    for party in scanned_package.parties:
                        Party.objects.create(
                            package=created_package,
                            type=party.type,
                            role=party.role,
                            name=party.name,
                            email=party.email,
                            url=party.url,
                        )

                    for dependency in scanned_package.dependencies:
                        DependentPackage.objects.create(
                            package=created_package,
                            purl=dependency.purl,
                            requirement=dependency.extracted_requirement,
                            scope=dependency.scope,
                            is_runtime=dependency.is_runtime,
                            is_optional=dependency.is_optional,
                            is_resolved=dependency.is_resolved,
                        )

                    created_package.last_modified_date = timezone.now()
                    created_package.save()
                    logger.debug(' + Inserted package\t: {}'.format(package_uri))

                    # Add this Package to the scan queue
                    _, created = ScannableURI.objects.get_or_create(
                        uri=package_uri,
                        package_id=created_package.id,
                    )
                    if created:
                        logger.debug(' + Inserted ScannableURI\t: {}'.format(package_uri))

    except Exception as e:
        msg = 'Error: Failed to map while processing ResourceURI: {}\n'.format(
            repr(resource_uri))
        msg += 'While processing scanned_package: {}\n'.format(
            repr(scanned_package))
        msg += get_error_message(e)
        logger.error(msg)
        # this is enough to save the error to the ResourceURI which is done at last
        map_error += msg

    # finally flag and save the processed resource_uri as mapped
    resource_uri.last_map_date = timezone.now()
    resource_uri.wip_date = None
    # always set the map error, resetting it to empty if the mapping was
    # succesful
    if map_error:
        resource_uri.map_error = map_error
    else:
        resource_uri.map_error = None
    resource_uri.save()


def merge_packages(existing_package, new_package_data, replace=False):
    """
    Merge the data from the `new_package_data` mapping into the
    `existing_package` Package model object.

    When an `existing_package` field has no value one side and and the
    new_package field has a value, the existing_package field is always
    set to this value.

    If `replace` is True and a field has a value on both sides, then
    existing_package field value will be replaced by the new_package
    field value. Otherwise if `replace` is False, the existing_package
    field value is left unchanged in this case.
    """
    existing_mapping = existing_package.to_dict()

    # We remove `purl` from `existing_mapping` because we use the other purl
    # fields (type, namespace, name, version, etc.) to generate the purl.
    existing_mapping.pop('purl')

    # FIXME REMOVE this workaround when a ScanCode bug fixed with
    # https://github.com/nexB/scancode-toolkit/commit/9b687e6f9bbb695a10030a81be7b93c8b1d816c2
    qualifiers = new_package_data.get('qualifiers')
    if isinstance(qualifiers, dict):
        # somehow we get an dict on the new value instead of a string
        # this not likely the best place to fix this
        new_package_data['qualifiers'] = normalize_qualifiers(qualifiers, encode=True)

    new_mapping = new_package_data

    for existing_field, existing_value in existing_mapping.items():
        new_value = new_mapping.get(existing_field)
        if TRACE:
            logger.debug(
                '\n'.join([
                    'existing_field:', repr(existing_field),
                    '    existing_value:', repr(existing_value),
                    '    new_value:', repr(new_value)])
            )

        # FIXME: handle Booleans??? though there are none for now

        # If the checksum from `new_package` is different than the one
        # existing checksum in `existing_package`, there is a big data
        # inconsistency issue and an Exception is raised
        if (existing_field in ('md5', 'sha1', 'sha256', 'sha512') and
                existing_value and
                new_value and
                existing_value != new_value):
            raise Exception(
                '\n'.join([
                    'Mismatched {} for {}:'.format(existing_field, existing_package.uri),
                    '    existing_value: {}'.format(existing_value),
                    '    new_value: {}'.format(new_value)
                ])
            )

        if not new_value:
            if TRACE:
                logger.debug('  No new value: skipping')
            continue

        if not existing_value or replace:
            if TRACE and not existing_value:
                logger.debug(
                    '  No existing value: set to new: {}'.format(new_value))

            if TRACE and replace:
                logger.debug(
                    '  Existing value and replace: set to new: {}'.format(new_value))

            if existing_field == 'parties':
                # If `existing_field` is `parties`, then we update the `Party` table
                parties = new_value
                if replace:
                    # Delete existing Party objects
                    Party.objects.filter(package=existing_package).delete()
                for party in parties:
                    _party, _created = Party.objects.get_or_create(
                        package=existing_package,
                        type=party['type'],
                        role=party['role'],
                        name=party['name'],
                        email=party['email'],
                        url=party['url'],
                    )
            elif existing_field == 'dependencies':
                # If `existing_field` is `dependencies`, then we update the `DependentPackage` table
                dependencies = new_value
                if replace:
                    # Delete existing DependentPackage objects
                    DependentPackage.objects.filter(package=existing_package).delete()
                for dependency in dependencies:
                    _dep, _created = DependentPackage.objects.get_or_create(
                        package=existing_package,
                        purl=dependency['purl'],
                        requirement=dependency['requirement'],
                        scope=dependency['scope'],
                        is_runtime=dependency['is_runtime'],
                        is_optional=dependency['is_optional'],
                        is_resolved=dependency['is_resolved'],
                    )
            else:
                # If `existing_field` is not `parties` or `dependencies`, then the
                # `existing_field` is a regular field on the Package model and can
                # be updated normally.
                setattr(existing_package, existing_field, new_value)
                existing_package.save()

        if TRACE:
            logger.debug('  Nothing done')
