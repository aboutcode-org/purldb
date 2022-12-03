#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
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
