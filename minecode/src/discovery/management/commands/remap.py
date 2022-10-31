#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from discovery.models import ResourceURI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = 'Mark ResourceURIs for remapping to packages.'

    def handle(self, *args, **options):
        q1 = Q(uri__startswith='https://repo1')
        q2 = Q(uri__startswith='maven-index://')
        q3 = Q(uri__startswith='https://replicate')
        q4 = Q(uri__startswith='https://registry')

        for uri in ResourceURI.objects.successfully_mapped().filter(q1 | q2 | q3 | q4):
            uri.last_map_date = None
            uri.wip_date = None
            uri.save()

        ResourceURI.objects.successfully_mapped().filter(uri__contains='maven').update(last_map_date=None)
        ResourceURI.objects.successfully_mapped().filter(uri__contains='npm').update(last_map_date=None)

        ResourceURI.objects.successfully_mapped().exclude(uri__startswith='http://repo1').exclude(uri__startswith='maven-index://').exclude(uri__startswith='https://replicate').exclude(uri__startswith='https://registry.npmjs.org').update(is_mappable=False)
