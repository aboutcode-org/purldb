#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import logging
import signal
import sys
import time

from django.db import transaction
from django.utils import timezone

from minecode.management.commands import VerboseCommand
from minecode.models import ScannableURI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 1


class ScanningCommand(VerboseCommand):
    """Base command class for processing ScannableURIs."""

    # subclasses must override
    logger = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--exit-on-empty",
            dest="exit_on_empty",
            default=False,
            action="store_true",
            help="Do not loop forever. Exit when the queue is empty.",
        )

        parser.add_argument(
            "--max-uris",
            dest="max_uris",
            default=0,
            action="store",
            help="Limit the number of Scannable URIs processed to a maximum number. "
            "0 means no limit. Used only for testing.",
        )

    def handle(self, *args, **options):
        exit_on_empty = options.get("exit_on_empty")
        max_uris = options.get("max_uris", 0)

        uris_counter = self.process_scans(
            exit_on_empty=exit_on_empty,
            max_uris=max_uris,
            # Pass options to allow subclasses to add their own options
            options=options,
        )
        self.stdout.write(f"Processed {uris_counter} ScannableURI.")

    @classmethod
    def process_scans(cls, exit_on_empty=False, max_uris=0, **kwargs):
        """
        Run an infinite scan processing loop. Return a processed URis count.

        Get the next available candidate ScannableURI and request a scan from
        ScanCode.io. Loops forever and sleeps a short while if there are no
        ScannableURI left to scan.
        """
        uris_counter = 0
        sleeping = False

        while True:
            # Wait before processing anything
            time.sleep(10)

            if cls.MUST_STOP:
                cls.logger.info("Graceful exit of the scan processing loop.")
                break

            if max_uris and uris_counter >= max_uris:
                cls.logger.info("max_uris requested reached: exiting scan processing loop.")
                break

            scannable_uri = cls.get_next_uri()

            if not scannable_uri:
                if exit_on_empty:
                    cls.logger.info("exit-on-empty requested: No more scannable URIs, exiting...")
                    break

                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    cls.logger.info(
                        f"No more scannable URIs, sleeping for at least {SLEEP_WHEN_EMPTY} seconds..."
                    )

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            cls.logger.info(f"Processing scannable URI: {scannable_uri}")

            cls.process_scan(scannable_uri, **kwargs)
            uris_counter += 1
            sleeping = False

        return uris_counter

    @classmethod
    def get_next_uri(self):
        """
        Return a locked ScannableURI for processing.
        Subclasses must implement

        Typically something like:
            with transaction.atomic():
                scannable_uri = ScannableURI.objects.get_next_scannable()
        """
        pass

    @classmethod
    def process_scan(scannable_uri, **kwargs):
        """
        Process a single `scannable_uri` ScannableURI. Subclasses must implement.
        If sucessfully processed the ScannableURI must be updated accordingly.
        """
        pass


class Command(ScanningCommand):
    logger = logger

    help = (
        "Check scancode.io requested scans for status then fetch and process "
        "completed scans for indexing and updates."
    )

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        ScanningCommand.handle(self, *args, **options)

    @classmethod
    def get_next_uri(self):
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_processable()
        return scannable_uri

    @classmethod
    def process_scan(
        cls,
        scannable_uri,
        get_scan_info_save_loc="",
        get_scan_data_save_loc="",
        **kwargs,
    ):
        """
        Manage a ScannableURI based on its status.
        - For submitted but not completed scans, check the timestamp of when the scan was submitted, if it has been past some time, then we set the scan as timed out
        - For timed out scans, we set that as failed and then create a new one?
        """
        logger.info(f"Checking scan for URI: {scannable_uri}")

        if scannable_uri.scan_status in (
            ScannableURI.SCAN_SUBMITTED,
            ScannableURI.SCAN_IN_PROGRESS,
        ):
            scan_duration = timezone.now() - scannable_uri.scan_date
            scan_duration_hours = scan_duration.seconds / (60 * 60)

            if scan_duration_hours > 2:
                scannable_uri.scan_status = ScannableURI.SCAN_TIMEOUT
                scannable_uri.wip_date = None
                scannable_uri.save()
                logger.info(f"Scan for URI has timed out: {scannable_uri}")


# support graceful death when used as a service
signal.signal(signal.SIGTERM, Command.stop_handler)
