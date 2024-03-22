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

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.management.commands import get_error_message
from minecode.management.commands import VerboseCommand
from minecode.models import PriorityResourceURI
from minecode.models import ScannableURI
from minecode.route import NoRouteAvailable


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)

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


class Command(VerboseCommand):
    help = 'Run a Package request queue.'

    def handle(self, *args, **options):
        """
        Get the next processable PriorityResourceURI and start the
        processing. Loops forever and sleeps a short while if there are
        no PriorityResourceURI left to process.
        """

        global MUST_STOP

        sleeping = False
        processed_counter = 0

        while True:
            if MUST_STOP:
                logger.info('Graceful exit of the request queue.')
                break

            with transaction.atomic():
                priority_resource_uri = PriorityResourceURI.objects.get_next_request()

            if not priority_resource_uri:
                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    logger.info('No more processable request, sleeping...')

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            sleeping = False

            # process request
            logger.info('Processing {}'.format(priority_resource_uri))
            try:
                errors = process_request(priority_resource_uri)
            except Exception as e:
                errors = 'Error: Failed to process PriorityResourceURI: {}\n'.format(
                    repr(priority_resource_uri))
                errors += get_error_message(e)
            finally:
                if errors:
                    priority_resource_uri.processing_error = errors
                    logger.error(errors)
                priority_resource_uri.processed_date = timezone.now()
                priority_resource_uri.wip_date = None
                priority_resource_uri.save()
                processed_counter += 1

        return processed_counter


def process_request(priority_resource_uri, _priority_router=priority_router):
    purl_to_visit = priority_resource_uri.uri
    source_purl = priority_resource_uri.source_uri
    try:
        if TRACE:
            logger.debug('visit_uri: uri: {}'.format(purl_to_visit))
        kwargs = dict()
        if source_purl:
            kwargs["source_purl"] = source_purl
        errors = _priority_router.process(purl_to_visit, **kwargs)
        if TRACE:
            new_uris_to_visit = list(new_uris_to_visit or [])
            logger.debug('visit_uri: new_uris_to_visit: {}'.format(new_uris_to_visit))

        return errors

    except NoRouteAvailable:
        error = f'No route available for {purl_to_visit}'
        logger.error(error)
        # TODO: For now, when a route is not yet supported, we keep a value for
        # the wip_date value so the instance is not back in the queue. It will
        # not be selected by a worker again until the wip_date is manually
        # cleared. This manual cleaning should be done once the support for the
        # route was added. It would be best if the clearing was automatic when
        # a route is added.
        return error
