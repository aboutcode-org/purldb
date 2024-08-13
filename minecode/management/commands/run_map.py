#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import signal
import sys
import time

from django.db import transaction
from django.utils import timezone

from minecode import map_router

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import mappers  # NOQA
from minecode import visitors  # NOQA
from minecode.management.commands import VerboseCommand
from minecode.management.commands import get_error_message
from minecode.model_utils import merge_or_create_package
from minecode.models import ResourceURI
from minecode.models import ScannableURI

TRACE = True

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 10

MUST_STOP = False


def stop_handler(*args, **kwargs):
    """Signal handler to set global variable to True."""
    global MUST_STOP
    MUST_STOP = True


signal.signal(signal.SIGTERM, stop_handler)

# number of mappable ResourceURI processed at once
MAP_BATCH_SIZE = 10


class Command(VerboseCommand):
    help = "Run a mapping worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--exit-on-empty",
            dest="exit_on_empty",
            default=False,
            action="store_true",
            help="Do not loop forever. Exit when the queue is empty.",
        )

    def handle(self, *args, **options):
        """
        Get the next available candidate ResourceURI and start the processing.
        Loops forever and sleeps a short while if there are no ResourceURI left to map.
        """
        global MUST_STOP

        logger.setLevel(self.get_verbosity(**options))
        exit_on_empty = options.get("exit_on_empty")

        sleeping = False

        while True:
            if MUST_STOP:
                logger.info("Graceful exit of the map loop.")
                break

            mappables = ResourceURI.objects.get_mappables()[:MAP_BATCH_SIZE]

            if not mappables:
                if exit_on_empty:
                    logger.info("No mappable resource, exiting...")
                    break

                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    logger.info("No mappable resource, sleeping...")

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            sleeping = False

            for resource_uri in mappables:
                logger.info(f"Mapping {resource_uri}")
                map_uri(resource_uri)


def map_uri(resource_uri, _map_router=map_router):
    """
    Call a mapper for a ResourceURI.
    `_map_router` is the Router to use for routing. Used for tests only.
    """
    # FIXME: returning a string or sequence is UGLY
    try:
        mapped_scanned_packages = _map_router.process(
            resource_uri.uri, resource_uri=resource_uri
        )

        logger.debug(f"map_uri: Package URI: {resource_uri.uri}")

        # consume generators
        mapped_scanned_packages = mapped_scanned_packages and list(
            mapped_scanned_packages
        )

        if not mapped_scanned_packages:
            msg = "No visited scanned packages returned."
            logger.error(msg)
            resource_uri.last_map_date = timezone.now()
            resource_uri.map_error = msg
            resource_uri.save()
            return

    except Exception as e:
        msg = f"Error: Failed to map while processing ResourceURI: {repr(resource_uri)}\n"
        msg += get_error_message(e)
        logger.error(msg)
        # we had an error, so mapped_scanned_packages is an error string
        resource_uri.last_map_date = timezone.now()
        resource_uri.map_error = msg
        resource_uri.save()
        return

    # if we reached this place, we have mapped_scanned_packages that contains
    # packages in ScanCode models format that these are ready to save to the DB

    map_error = ""

    try:
        with transaction.atomic():
            # iterate the ScanCode Package objects returned by the mapper
            # and either save these as new packagedb.Packages or update and
            # existing one

            for scanned_package in mapped_scanned_packages:
                visit_level = resource_uri.mining_level
                package, package_created, _, m_err = merge_or_create_package(
                    scanned_package, visit_level
                )
                map_error += m_err
                if package_created:
                    # Add this Package to the scan queue
                    package_uri = scanned_package.download_url
                    _, scannable_uri_created = ScannableURI.objects.get_or_create(
                        uri=package_uri,
                        package=package,
                    )
                    if scannable_uri_created:
                        logger.debug(
                            f" + Inserted ScannableURI\t: {package_uri}"
                        )

    except Exception as e:
        msg = f"Error: Failed to map while processing ResourceURI: {repr(resource_uri)}\n"
        msg += f"While processing scanned_package: {repr(scanned_package)}\n"
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
