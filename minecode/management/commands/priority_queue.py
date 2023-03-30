#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from collections import Counter
import logging
import signal
import sys
import time

# FIXME: why use Django cache for this? any benefits and side effects?
from django.core.cache import cache as visit_delay_by_hostname
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import smart_str

import reppy.cache

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import mappers  # NOQA
from minecode import visitors  # NOQA
from minecode import visit_router

from minecode.management.commands import get_error_message
from minecode.management.commands import VerboseCommand

from minecode.models import PriorityResourceURI
from minecode.route import NoRouteAvailable

from packageurl import PackageURL

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 10

# Create a global cache for robots.txt. Note that this is process specific and does
# not span multiple workers
robots = reppy.cache.RobotsCache()
# reppy.logger.setLevel(logging.DEBUG)

# FIXME: we should rotate UA strings or setup our own UA
# this one is for FF Windows 7 agent 32 on win7 64 as of July 2016
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0'

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
            processed_counter += 1

            # Create function to process purl
            process_request(priority_resource_uri)

        return processed_counter


def process_request(priority_resource_uri):
    purl = priority_resource_uri.package_url
    purl = PackageURL.from_string(purl)

    maven_api_stub = f"https://search.maven.org/solrsearch/select?q={}"
    coordinates = []
    if purl.namespace:
        coordinates.append(f'g:{purl.namespace}')
    if purl.name:
        coordinates.append(f'a:{purl.name}')
    if purl.version:
        coordinates.append(f'v:{purl.version}')
    

    https://search.maven.org/solrsearch/select?q=g:com.google.inject%20AND%20a:guice%20AND%20v:3.0%20AND%20l:javadoc%20AND%20p:jar&rows=20&wt=json
    pass


def visit_uri(resource_uri, max_uris=0, uri_counter_by_visitor=None, _visit_router=visit_router):
    """
    Call a visitor for a single ResourceURI. Process up to `max_uris` records.
    `_visit_router` is the Router to use for routing. Used for tests only.
    """
    from requests.exceptions import ConnectionError, Timeout

    if not resource_uri:
        return

    uri_to_visit = resource_uri.uri

    if uri_counter_by_visitor is None:
        uri_counter_by_visitor = Counter()

    visit_errors = []
    new_uris_to_visit = visited_data = visit_error = None

    try:
        # Get the visitor class names
        visitor = _visit_router.resolve(uri_to_visit)
        visitor_key = visitor.__module__ + visitor.__name__
        if max_uris:
            # check if we are > the max_uri value for that ResourceURI string
            # if not, we break
            num_visits = uri_counter_by_visitor.get(visitor_key) or 0
            if num_visits > max_uris:
                return 0

        if TRACE:
            logger.debug('visit_uri: uri: {}'.format(uri_to_visit))

        # TODO: Consider pass a full visitors.URI plain object rather than a plain string
        new_uris_to_visit, visited_data, visit_error = _visit_router.process(uri_to_visit)
        if TRACE:
            new_uris_to_visit = list(new_uris_to_visit or [])
            logger.debug('visit_uri: new_uris_to_visit: {}'.format(new_uris_to_visit))

    except NoRouteAvailable:
        logger.error('No route available.')
        # TODO: For now, when a route is not yet supported, we keep a value for
        # the wip_date value so the instance is not back in the queue. It will
        # not be selected by a worker again until the wip_date is manually
        # cleared. This manual cleaning should be done once the support for the
        # route was added. It would be best if the clearing was automatic when
        # a route is added.
        return 0
    except (ConnectionError, Timeout, Exception) as e:
        # FIXME: is catching all expections here correct?
        msg = 'Visit error for URI: {}'.format(uri_to_visit)
        msg += '\n'.format(uri_to_visit)
        msg += get_error_message(e)
        visit_errors.append(msg)
        logger.error(msg)

    ########################################
    # Also log visit errors!!!1
    if visit_error:
        msg = 'Visit error for URI: {}'.format(uri_to_visit)
        msg += '\n'.format(uri_to_visit)
        msg += get_error_message(e)
        visit_errors.append(msg)
        logger.error(msg)

    ########################################
    ########################################
    # uris needs to be an iterable (list, set, generator...)
    new_uris_to_visit = new_uris_to_visit or []

    inserted_count = 0

    try:
        # NOTE: new_uris_to_visit here is an iterable of visitors.URI
        # objects, NEITHER strings NOR ResourceURI models
        # TODO: use batching for inserts or create for more efficient DB processing
        for vuri_count, vuri in enumerate(new_uris_to_visit):
            # FIXME: should we really do this smart_str here??
            uri_str = smart_str(vuri.uri)
            visited_uri = vuri.to_dict()

            last_modified_date = visited_uri.pop('date')
            if last_modified_date:
                visited_uri['last_modified_date'] = last_modified_date

            if vuri_count % 1000 == 0:
                logger.debug(' * Processed: {} visited URIs'.format(vuri_count))

            try:
                # insert new if pre-visited
                pre_visited = visited_uri.pop('visited')
                if pre_visited:
                    # set last visit date for this pre-visited URI
                    visited_uri['last_visit_date'] = timezone.now()
                    new_uri = ResourceURI(**visited_uri)
                    new_uri.save()
                    logger.debug(' + Inserted pre-visited:\t{}'.format(uri_str))
                    inserted_count += 1
                    if max_uris:
                        uri_counter_by_visitor[visitor_key] += 1
                else:
                    # if not pre-visited only insert if not existing
                    if not ResourceURI.objects.filter(uri=vuri.uri, last_visit_date=None).exists():
                        visited_uri['last_visit_date'] = None
                        new_uri = ResourceURI(**visited_uri)
                        new_uri.save()
                        logger.debug(' + Inserted new:\t{}'.format(uri_str))
                        inserted_count += 1
                        if max_uris:
                            uri_counter_by_visitor[visitor_key] += 1
                    else:
                        logger.debug(' + NOT Inserted:\t{}'.format(uri_str))

            except Exception as e:
                # FIXME: is catching all expections here correct?
                msg = 'ERROR while processing URI from a visit through: {}'.format(uri_str)
                msg += '\n'
                msg += repr(visited_uri)
                msg += '\n'
                msg += get_error_message(e)
                visit_errors.append(msg)
                logger.error(msg)
                if len(visit_errors) > 10:
                    logger.error(' ! Breaking after processing over 10 vuris errors for: {}'.format(uri_str))
                    break

            if max_uris and int(uri_counter_by_visitor[visitor_key]) > int(max_uris):
                logger.info(' ! Breaking after processing max-uris: {} URIs.'.format(max_uris))
                break

    except Exception as e:
        msg = 'Visit error for URI: {}'.format(uri_to_visit)
        msg += '\n'.format(uri_to_visit)
        msg += get_error_message(e)
        visit_errors.append(msg)
        logger.error(msg)

    finally:
        # Flag the processed resource_uri as completed and attach data.
        resource_uri.last_visit_date = timezone.now()
        resource_uri.wip_date = None
        if visited_data:
            logger.debug(' + Data collected.')
            resource_uri.data = visited_data
        if visit_errors:
            logger.debug(' ! Errors.')
            resource_uri.visit_error = '\n'.join(visit_errors)[:5000]
        resource_uri.save()

    logger.debug(' Inserted\t: {} new URI(s).'.format(inserted_count))
    return inserted_count
