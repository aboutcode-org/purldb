#
# Copyright (c) nexB Inc. and others. All rights reserved.
# PurlDB is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from django.core.management.base import BaseCommand

from aboutcode.federatedcode.client import subscribe_package


class Command(BaseCommand):
    help = "Subscribe package for their metadata update from FederatedCode."

    def add_arguments(self, parser):
        parser.add_argument(
            "purl", type=str, help="Specify a PURL to subscribe for updates."
        )

    def handle(self, *args, **options):
        purl = options.get("purl")

        federatedcode_host = "http://127.0.0.1:8000/"
        remote_username = "purldb"

        response = subscribe_package(federatedcode_host, remote_username, purl)

        style = self.style.ERROR
        if response.status_code == 200:
            style = self.style.SUCCESS

        self.stdout.write(
            response.text,
            style,
        )
