#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from clearcode.store_scans import store_scancode_scans_from_cd_items
from minecode.management.commands import VerboseCommand

class Command(VerboseCommand):
    help = 'Store scancode scans in git repositories'

    def add_arguments(self, parser):
        parser.add_argument('work_dir', type=str)
        parser.add_argument('--github_org', type=str, default="")
        parser.add_argument('--count', type=int, default=0)

    def handle(self, *args, **options):
        store_scancode_scans_from_cd_items(work_dir=options['work_dir'], github_org=options['github_org'], count=options['count'])