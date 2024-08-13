#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#


import logging
import sys

from minecode.management.commands import VerboseCommand
from minecode.management.commands import get_error_message
from minecode.models import ScannableURI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(VerboseCommand):
    logger = logger

    help = "Increase the priority of the Package to be scanned"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pattern",
            "-p",
            action="store",
            dest="pattern",
            help="Only increase the priority of URIs matching this regex pattern.",
        )

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))

        pattern = options.get("pattern")

        for scannable_uri in ScannableURI.objects.filter(uri__iregex=pattern):
            uri = scannable_uri.uri
            try:
                # Priority is arbitrarily set to 100 to immediately increase its processing priority
                scannable_uri.priority = 100
                scannable_uri.save()
                logger.info(f"Increased priority of: <ScannableURI: {uri}>")
            except Exception as e:
                msg = f"Error setting priority for: <ScannableURI: {uri}>"
                msg += get_error_message(e)
                logger.error(msg)
