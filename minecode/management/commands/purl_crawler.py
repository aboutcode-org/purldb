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


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


WORKER_FUNCS = {}


class Command(VerboseCommand):
    help = "Run a visiting worker loop to collect package purls to files and commit to repo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            dest="repo",
            default=None,
            action="store_false",
            help="specify which repo to visit",
        )

    def handle(self, *args, **options):
        """
        Get repo to visit
        """
        logger.setLevel(self.get_verbosity(**options))
        repo = options.get("repo")
        if not repo:
            self.stderr.write("repo required")
            sys.exit(-1)
        repo = str(repo).lower()
        if worker_func := WORKER_FUNCS.get(repo):
            for purls in worker_func():
                # TODO: check out repo
                # TODO: create directory for package, if not available
                # TODO: save purls to yaml
                # TODO: commit and push
                pass
