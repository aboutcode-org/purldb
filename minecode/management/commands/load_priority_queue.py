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

import requests

from commoncode.resource import VirtualCodebase
from minecode.management.commands import VerboseCommand
from minecode.models import PriorityResourceURI


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = 'Run a Package request queue.'

    def add_arguments(self, parser):
        parser.add_argument("--input", type=str)

    def handle(self, *args, **options):
        input = options.get('input')
        if input:
            vc = VirtualCodebase(location=input)
            for resource in vc.walk():
                if not resource.sha1:
                    continue
                maven_api_search_url = f'https://search.maven.org/solrsearch/select?q=1:{resource.sha1}'
                response = requests.get(maven_api_search_url)
                if not response.ok:
                    logger.error(f"API query failed for: {maven_api_search_url}")
                    continue
                contents = response.json()
                resp = contents.get('response', {})
                if resp.get('numFound', 0) > 0:
                    for matched_package in resp.get('docs', []):
                        namespace = matched_package.get('g', '')
                        name = matched_package.get('a', '')
                        version = matched_package.get('v', '')
                        if namespace and name and version:
                            purl = f'pkg:maven/{namespace}/{name}@{version}'
                            PriorityResourceURI.objects.create(uri=purl, package_url=purl)
                            logger.info(f'Added {purl} to priority queue')
