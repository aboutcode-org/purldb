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

from django.db import transaction
from django.utils import timezone

from packageurl import normalize_qualifiers

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import mappers  # NOQA
from minecode import visitors  # NOQA

from minecode import map_router
from minecode.models import ResourceURI
from packagedb.models import DependentPackage
from packagedb.models import Party
from minecode.management.commands import get_error_message
from minecode.management.commands import VerboseCommand
from minecode.model_utils import merge_or_create_package
from minecode.models import ScannableURI


TRACE = True

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
                visit_level = resource_uri.mining_level
                package, package_created, _, m_err = merge_or_create_package(scanned_package, visit_level)
                map_error += m_err
                if package_created:
                    # Add this Package to the scan queue
                    package_uri = scanned_package.download_url
                    _, scannable_uri_created = ScannableURI.objects.get_or_create(
                        uri=package_uri,
                        package=package,
                    )
                    if scannable_uri_created:
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

    fields_to_skip = ('package_uid',)

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
                        requirement=dependency['extracted_requirement'],
                        scope=dependency['scope'],
                        is_runtime=dependency['is_runtime'],
                        is_optional=dependency['is_optional'],
                        is_resolved=dependency['is_resolved'],
                    )
            elif existing_field in fields_to_skip:
                # Continue to next field
                continue
            else:
                # If `existing_field` is not `parties` or `dependencies`, then the
                # `existing_field` is a regular field on the Package model and can
                # be updated normally.
                setattr(existing_package, existing_field, new_value)
                existing_package.save()

        if TRACE:
            logger.debug('  Nothing done')
