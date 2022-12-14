#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import json
import logging
import sys

from django.core.management.base import BaseCommand

# NOTE: mappers and visitors are Unused Import here: But importing the mappers
# module triggers routes registration
from discovery import mappers  # NOQA
from discovery import visitors  # NOQA
from discovery import map_router
from discovery import visit_router
from discovery.models import ResourceURI
from discovery.route import NoRouteAvailable

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = 'Print diagnostic information on a given URI prefix.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--uri-prefix',
            dest='uri_prefix',
            action='store',
            help='URI prefix to check.')
        parser.add_argument(
            '--limit',
            dest='limit',
            default=10,
            action='store',
            help='Maximum number of records to return.')
        parser.add_argument(
            '--show-data',
            dest='show_data',
            default=False,
            action='store_true',
            help='URI prefix to check.')

    def handle(self, *args, **options):
        """
        Check uris and print diagnostic information as JSON.
        """
        uri_prefix = options.get('uri_prefix')
        limit = options.get('limit', 10)
        show_data = options.get('show_data')

        # get the last 10 uris
        uris = ResourceURI.objects.filter(uri__startswith=uri_prefix).order_by("-id")[:limit]

        # TODO: add if the uri be resolved by visit and/or map router
        for uri in uris:

            try:
                # FIXME: resolve() returns an acutal Visitor object, using module names for now
                visit_route_resolve = repr(visit_router.resolve(uri.uri))
            except NoRouteAvailable:
                visit_route_resolve = 'No Route Availible'

            try:
                # FIXME: resolve() returns an acutal Mapper object, using module names for now
                map_route_resolve = repr(map_router.resolve(uri.uri))
            except NoRouteAvailable:
                map_route_resolve = 'No Route Availible'

            if uri.last_visit_date:
                last_visit_date = uri.last_visit_date.isoformat()
            else:
                last_visit_date = None

            if uri.last_map_date:
                last_map_date = uri.last_map_date.isoformat()
            else:
                last_map_date = None

            if uri.wip_date:
                wip_date = uri.wip_date.isoformat()
            else:
                wip_date = None

            uri_info = dict([
                ('id', uri.id),
                ('uri', uri.uri),
                ('source_uri', uri.source_uri),
                ('priority', uri.priority),
                ('mining_level', uri.mining_level),
                ('visit_route', visit_route_resolve),
                ('map_route', map_route_resolve),
                ('is_visitable', uri.is_visitable),
                ('is_mappable', uri.is_mappable),
                ('last_visit_date', last_visit_date),
                ('last_map_date', last_map_date),
                ('wip_date', wip_date),
                ('visit_error', uri.visit_error),
                ('map_error', uri.map_error),
            ])

            if show_data:
                uri_info.update({'data': uri.data})

            print(json.dumps(uri_info, indent=2))
