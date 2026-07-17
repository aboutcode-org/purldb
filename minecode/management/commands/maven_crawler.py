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

from minecode.collectors.maven import crawl_maven_repo_from_root
from minecode.management.commands import VerboseCommand

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = "Run a Package request queue."

    def handle(self, *args, **options):
        # Add the maven root URLs
        # Ref: https://github.com/aboutcode-org/purldb/issues/630#issuecomment-3599942716
        maven_root_urls = [
            "https://repo.maven.apache.org/maven2",
            "https://repo.spring.io/artifactory/milestone",
            "https://plugins.gradle.org/m2",
            "https://repository.apache.org/content/groups/snapshots",
            "https://repository.jboss.org/nexus/service/rest/repository/browse/releases",
            "https://repository.jboss.org/nexus/service/rest/repository/browse/public",
        ]
        for maven_root_url in maven_root_urls:
            crawl_maven_repo_from_root(root_url=maven_root_url)
