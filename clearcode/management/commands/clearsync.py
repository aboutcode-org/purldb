#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from clearcode.sync import sync
from minecode.management.commands import VerboseCommand


class Command(VerboseCommand):
    help = """
    Fetch the latest definitions and harvests from ClearlyDefined and save these
    as gzipped JSON either as as files in output-dir or in a PostgreSQL
    database. Loop forever after waiting some seconds between each cycles.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            dest="output_dir",
            default=None,
            type=str,
            help="Save fetched content as compressed gzipped files to this output directory.",
        )
        parser.add_argument(
            "--save-to-db",
            dest="save_to_db",
            action="store_true",
            help="Save fetched content as compressed gzipped blobs in the configured database.",
        )
        parser.add_argument(
            "--unsorted",
            dest="unsorted",
            action="store_true",
            help="Fetch data without any sorting. The default is to fetch data sorting by latest updated first.",
        )
        parser.add_argument(
            "--base-api-url",
            dest="base_api_url",
            default="https://api.clearlydefined.io",
            help="ClearlyDefined base API URL.",
        )
        parser.add_argument(
            "--wait",
            dest="wait",
            default=60,
            type=int,
            help="Set the number of seconds to wait for new or updated definitions "
            "between two loops.",
        )
        parser.add_argument(
            "-n",
            "--processes",
            dest="processes",
            default=1,
            type=int,
            help="Set the number of parallel processes to use. Disable parallel processing if 0.",
        )
        parser.add_argument(
            "--max-def",
            dest="max_def",
            default=0,
            type=int,
            help="Set the maximum number of definitions to fetch.",
        )
        parser.add_argument(
            "--only-definitions",
            dest="only_definitions",
            action="store_true",
            help="Only fetch definitions and no other data item.",
        )
        parser.add_argument(
            "--log-file",
            dest="log_file",
            default=None,
            type=str,
            help="Path to a file where to log fetched paths, one per line. "
            "Log entries will be appended to this file if it exists.",
        )
        parser.add_argument(
            "--verbose",
            dest="verbose",
            action="store_true",
            help="Display more verbose progress messages.",
        )

    def handle(self, *args, **options):
        output_dir = options.get("output_dir")
        save_to_db = options.get("save_to_db")
        base_api_url = options.get("base_api_url")
        wait = options.get("wait")
        processes = options.get("processes")
        unsorted = options.get("unsorted")
        log_file = options.get("log_file")
        max_def = options.get("max_def")
        only_definitions = options.get("only_definitions")
        verbose = options.get("verbose")

        sync(
            output_dir=output_dir,
            save_to_db=save_to_db,
            base_api_url=base_api_url,
            wait=wait,
            processes=processes,
            unsorted=unsorted,
            log_file=log_file,
            max_def=max_def,
            only_definitions=only_definitions,
            verbose=verbose,
        )
