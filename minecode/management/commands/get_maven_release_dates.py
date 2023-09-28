#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from dateutil.parser import parse as dateutil_parse
import logging
import sys

import requests

from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from minecode.visitors.maven import collect_links_from_text
from minecode.visitors.maven import filter_for_artifacts
from os.path import dirname

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = ''

    def handle(self, *args, **options):
        maven_packages = Package.objects.filter(type='maven', release_date=None)
        for package in maven_packages:
            download_url = package.download_url
            package_version_page_url = dirname(download_url)
            filename = download_url.rsplit('/')[-1]
            response = requests.get(package_version_page_url)
            if response:
                timestamps_by_links = collect_links_from_text(response.text, filter=filter_for_artifacts)
                timestamp = timestamps_by_links.get(filename)
                if not timestamp:
                    continue
                timestamp = dateutil_parse(timestamp)
                package.release_date = timestamp
                # TODO: do batch update
                package.save()
