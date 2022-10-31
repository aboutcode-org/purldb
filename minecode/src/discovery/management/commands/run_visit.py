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
from discovery import mappers  # NOQA
from discovery import visitors  # NOQA
from discovery import visit_router

from discovery.management.commands import get_error_message
from discovery.management.commands import VerboseCommand

from discovery.models import ResourceURI
from discovery.route import NoRouteAvailable


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
    help = 'Run a visiting worker loop.'

    # Note: we use the GLOBAL visit_router by default here.
    # Test subclasses can override this class-level attribute for testing.
    router = visit_router

    def add_arguments(self, parser):
        parser.add_argument(
            '--exit-on-empty',
            dest='exit_on_empty',
            default=False,
            action='store_true',
            help='Do not loop forever. Exit when the queue is empty.')

        parser.add_argument(
            '--max-uris',
            dest='max_uris',
            default=0,
            action='store',
            help='Limit the number of URIs yielded from a visit to a maximum '
                 'number. 0 means no limit. Used only for testing.')

        parser.add_argument(
            '--max-loops',
            dest='max_loops',
            default=0,
            action='store',
            help='Limit the number of visit loops to a maximum number. '
                 '0 means no limit. Used only for testing.')

        parser.add_argument(
            '--ignore-robots',
            dest='ignore_robots',
            default=False,
            action='store_true',
            help='Ignore robots.txt politeness.')

        parser.add_argument(
            '--ignore-throttle',
            dest='ignore_throttle',
            default=False,
            action='store_true',
            help='Ignore throttling politeness.')

    def handle(self, *args, **options):
        """
        Get the next available candidate ResourceURI and start the
        processing. Loops forever and sleeps a short while if there are
        no ResourceURI left to visit.
        """
        logger.setLevel(self.get_verbosity(**options))
        exit_on_empty = options.get('exit_on_empty')
        max_uris = options.get('max_uris', 0)
        max_uris = int(max_uris)
        max_loops = options.get('max_loops', 0)
        ignore_robots = options.get('ignore_robots')
        ignore_throttle = options.get('ignore_throttle')

        visited_counter, inserted_counter = visit_uris(
            ignore_robots=ignore_robots,
            ignore_throttle=ignore_throttle,
            exit_on_empty=exit_on_empty,
            max_loops=max_loops,
            max_uris=max_uris,
        )

        self.stdout.write('Visited {} URIs'.format(visited_counter))
        self.stdout.write('Inserted {} new URIs'.format(inserted_counter))


def visit_uris(ignore_robots=False, ignore_throttle=False,
               exit_on_empty=False, max_loops=0, max_uris=0,
               user_agent=USER_AGENT):
    """
    Run an infinite visit loop. Return a tuple of (visited, inserted)
    counts.

    Get the next available candidate ResourceURI and start processing.
    Loop forever and sleeps a short while if there are no ResourceURI
    left to visit.

    Process throttles and robots.txt politeness
    """
    global MUST_STOP

    visited_counter = 0
    inserted_counter = 0
    uri_counter_by_visitor = Counter()

    sleeping = False

    while True:
        if MUST_STOP:
            logger.info('Graceful exit of the visit loop.')
            break

        with transaction.atomic():
            resource_uri = ResourceURI.objects.get_next_visitable()

        if not resource_uri:
            if exit_on_empty:
                logger.info('exit-on-empty requested: No more visitable resource, exiting...')
                break

            # Only log a single message when we go to sleep
            if not sleeping:
                sleeping = True
                logger.info('No more visitable resource, sleeping...')

            time.sleep(SLEEP_WHEN_EMPTY)
            continue

        sleeping = False

        if not ignore_robots and robots.disallowed(resource_uri.uri, user_agent):
            msg = 'Denied by robots.txt'
            logger.error(msg)
            resource_uri.last_visit_date = timezone.now()
            resource_uri.wip_date = None
            resource_uri.visit_error = msg
            resource_uri.save()
            continue

        if not ignore_throttle:
            sleep_time = get_sleep_time(resource_uri)
            if sleep_time:
                logger.debug('Respecting revisit delay: wait for {} for {}'.format(sleep_time, resource_uri.uri))
                time.sleep(sleep_time)
            # Set new value in cache 'visit_delay_by_hostname' right before making the request
            # TODO: The cache logic should move closer to the requests calls
            uri_hostname = reppy.Utility.hostname(resource_uri.uri)
            visit_delay_by_hostname.set(uri_hostname, timezone.now())

        # visit proper
        logger.info('Visiting {}'.format(resource_uri))
        visited_counter += 1

        inserted_counter += visit_uri(
            resource_uri=resource_uri, max_uris=max_uris,
            uri_counter_by_visitor=uri_counter_by_visitor)

        if max_loops and int(visited_counter) > int(max_loops):
            logger.info('Stopping visits after max_loops: {} visit loops.'.format(max_loops))
            break

    return visited_counter, inserted_counter


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


def get_sleep_time(resource_uri, minimum_delay_between_visits=1, user_agent=USER_AGENT):
    """
    Return the sleep time in seconds the worker should wait in order to
    respect the robots.txt delays and be polite. At the minimum return the
    `minimum_delay_between_visits` as seconds.

    To be polite when we need to be polite
    """
    delay = robots.delay(url=resource_uri.uri, agent=user_agent)

    if not delay:
        return minimum_delay_between_visits

    uri_hostname = reppy.Utility.hostname(resource_uri.uri)
    cached_delay = visit_delay_by_hostname.get(uri_hostname)

    if cached_delay:
        delta = (timezone.now() - cached_delay).total_seconds()
        # Spend less time processing than required delay
        if delta < delay:
            return delay - delta
