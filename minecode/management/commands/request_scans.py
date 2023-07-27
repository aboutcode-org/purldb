#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import signal
import sys

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from minecode.management import scanning
from minecode.management.commands import get_error_message
from minecode.models import ScannableURI


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(scanning.ScanningCommand):
    logger = logger

    help = 'Request scans for ScannableURIs from scancode.io.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-scan-requests',
            dest='max_scan_requests',
            action='store',
            help='Limit the number of scan requests that can be made',
            default=3,
        )

    def handle(self, *args, **options):
        self.logger.setLevel(self.get_verbosity(**options))
        scanning.ScanningCommand.handle(self, *args, **options)

    @classmethod
    def get_next_uri(self):
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_scannable()
        return scannable_uri

    @classmethod
    def process_scan(cls, scannable_uri, options, response_save_loc='', **kwargs):
        """
        Request a ScanCode.io scan for a `scannable_uri` ScannableURI.
        """
        uri = scannable_uri.uri
        max_scan_requests = options.get('max_scan_requests', 3)
        if isinstance(max_scan_requests, int):
            submitted_and_in_progress = ScannableURI.objects.filter(
                Q(scan_status=ScannableURI.SCAN_SUBMITTED) | Q(scan_status=ScannableURI.SCAN_IN_PROGRESS)
            ).count()

            if submitted_and_in_progress >= max_scan_requests:
                cls.logger.info(f'Max scan requests reached: {max_scan_requests} Skipping URI "{uri}"')
                return

        scan_errors = []
        scancodeio_uuid = scan_error = None

        try:
            cls.logger.info('Requesting scan from ScanCode.io for URI: "{uri}"'.format(**locals()))
            scan = scanning.submit_scan(
                uri,
                scannable_uri.package,
                api_url=cls.api_url,
                api_auth_headers=cls.api_auth_headers,
                response_save_loc=response_save_loc
            )
            scancodeio_uuid = scan.uuid

        except Exception as e:
            msg = 'Scan request error for URI: "{uri}"'.format(**locals())
            msg += '\n'.format(scannable_uri.uri)
            msg += get_error_message(e)
            scan_errors.append(msg)
            cls.logger.error(msg)

        finally:
            # Flag the processed scannable_uri as completed
            scannable_uri.scan_status = ScannableURI.SCAN_SUBMITTED
            scannable_uri.scan_request_date = timezone.now()
            scannable_uri.scan_uuid = scancodeio_uuid
            scannable_uri.wip_date = None

            if scan_errors:
                cls.logger.debug(' ! Scan request errors.')
                scannable_uri.scan_error = '\n'.join(scan_errors)[:5000]
            else:
                cls.logger.debug(' + Scan requested OK.')

            scannable_uri.save()


# support graceful death when used as a service
signal.signal(signal.SIGTERM, Command.stop_handler)
