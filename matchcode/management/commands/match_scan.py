#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.core.management.base import BaseCommand

from matchcode import match


class Command(BaseCommand):
    help = 'matches packages in a scancode fileinfo scan'

    def add_arguments(self, parser):
        parser.add_argument('scancode_file_path', type=str)
        parser.add_argument('outfile_path', type=str)

    def handle(self, *args, **options):
        scancode_file = options['scancode_file_path']
        outfile = options['outfile_path']

        # load up the scancode fileinfo json
        with open(scancode_file) as f:
            scan = json.load(f)

        results = match.match_packages(scan)

        # write new json results
        with open(outfile, 'w') as f:
            json.dump(results, f, indent=2)
