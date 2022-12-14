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

from discovery.models import ResourceURI
from packagedb.models import Package

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = 'Print status information for the minecode system.'

    def handle(self, *args, **options):
        counts = dict([
            ('total_packages', Package.objects.count()),
            ('total_uri', ResourceURI.objects.count()),
            ('unique_uri', ResourceURI.objects.distinct().count()),

            ('visitables', ResourceURI.objects.get_visitables().count()),
            ('visited', ResourceURI.objects.visited().count()),
            ('successfully_visited', ResourceURI.objects.successfully_visited().count()),
            ('unsuccessfully_visited', ResourceURI.objects.unsuccessfully_visited().count()),
            ('never_visited', ResourceURI.objects.never_visited().count()),
            ('visit_in_progress', ResourceURI.objects.filter(wip_date__isnull=False, last_visit_date__isnull=True).count()),

            ('mappables', ResourceURI.objects.get_mappables().count()),
            ('mapped', ResourceURI.objects.mapped().count()),
            ('successfully_mapped', ResourceURI.objects.successfully_mapped().count()),
            ('unsuccessfully_mapped', ResourceURI.objects.unsuccessfully_mapped().count()),
            ('never_mapped', ResourceURI.objects.never_mapped().count()),
        ])

        print(json.dumps(counts, indent=2))
