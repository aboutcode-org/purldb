#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#


import logging
import sys

from django.core.management.base import BaseCommand

from minecode.management.commands import get_error_message
from minecode.models import ScannableURI
from packagedb.models import Package

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    logger = logger

    help = "Create ScannableURIs from Packages"

    def handle(self, *args, **options):
        for package in Package.objects.all():
            package_uri = package.download_url
            try:
                _, created = ScannableURI.objects.get_or_create(
                    uri=package_uri, package=package
                )
                if created:
                    self.stdout.write(
                        f"ScannableURI created for: {package_uri}"
                    )
            except Exception as e:
                msg = f"Error creating ScannableURI for: {package_uri}"
                msg += get_error_message(e)
                logger.error(msg)
