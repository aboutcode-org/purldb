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
from purl2vcs.find_source_repo import get_source_package_for_all_packages

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(VerboseCommand):
    help = "Create source repo packages for Package object and add it to package sets"

    def handle(self, *args, **options):
        logger.info("Finding source repo for packages")
        get_source_package_for_all_packages()
