#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from clearcode.load import load
from minecode.management.commands import VerboseCommand


class Command(VerboseCommand):
    help = """
    Handle ClearlyDefined gzipped JSON scans by walking a clearsync directory structure,
    creating CDItem objects and loading them into a PostgreSQL database.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--input-dir',
            dest='input_dir',
            default=None,
            type=str,
            help='Load content from this input directory that contains a tree of gzip-compressed JSON CD files')
        parser.add_argument(
            '--cd-root-dir',
            dest='cd_root_dir',
            default=None,
            type=str,
            help='Specify root directory that contains a tree of gzip-compressed JSON CD files')

    def handle(self, *args, **options):
        input_dir = options.get('input_dir')
        cd_root_dir = options.get('cd_root_dir')

        load(
            input_dir=input_dir,
            cd_root_dir=cd_root_dir
        )
