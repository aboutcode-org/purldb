#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys

from minecode.management.commands import VerboseCommand
from minecode.models import ScannableURI


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = "Check for outstanding ScannableURIs and reset them."

    def handle(self, *args, **options):
        """
        Check for outstanding ScannableURIs and reset them.
        """
        reset_outstanding_scannableuris()


def reset_outstanding_scannableuris():
    outstanding_scannable_uris = ScannableURI.objects.get_outstanding_scannable_uris()
    if outstanding_scannable_uris.exists():
        logger.info(f"Resetting {outstanding_scannable_uris.count()} ScannableURIs")
        for scannable_uri in outstanding_scannable_uris:
            if TRACE:
                logger.debug(f"Resetting ScannableURI for: {scannable_uri}")
            scannable_uri.reset()
