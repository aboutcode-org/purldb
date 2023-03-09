#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import sys

from django.core.management.base import BaseCommand

from packagedb.models import Package
from minecode.management.commands import get_error_message
from minecode.models import ScannableURI


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    logger = logger

    help = 'Create ScannableURIs from Packages'

    def handle(self, *args, **options):
        for package in Package.objects.all():
            package_uri = package.download_url
            try:
                _, created = ScannableURI.objects.get_or_create(
                    uri=package_uri,
                    package=package
                )
                if created:
                    self.stdout.write('ScannableURI created for: {}'.format(package_uri))
            except Exception as e:
                msg = 'Error creating ScannableURI for: {}'.format(package_uri)
                msg += get_error_message(e)
                logger.error(msg)
