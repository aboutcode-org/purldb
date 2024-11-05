#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from minecode.management.user_creation import CreateUserCommand


class Command(CreateUserCommand):
    help = "Create a user and generate an API key for a scan queue worker"

    def handle(self, *args, **options):
        username = options["username"]
        interactive = options["interactive"]
        verbosity = options["verbosity"]
        self.create_user(
            username=username, interactive=interactive, verbosity=verbosity
        )
