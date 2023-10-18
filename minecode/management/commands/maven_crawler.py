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

from minecode.management.commands import VerboseCommand
from minecode.visitors.maven import crawl_maven_repo_from_root


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = 'Run a Package request queue.'

    def handle(self, *args, **options):
        maven_root_url = 'https://repo.maven.apache.org/maven2'
        crawl_maven_repo_from_root(root_url=maven_root_url)
