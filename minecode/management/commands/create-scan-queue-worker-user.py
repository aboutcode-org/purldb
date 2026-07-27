#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.contrib.auth.models import Group

import importlib

create_user = importlib.import_module("scanpipe.management.commands.create-user")


class Command(create_user.Command):
    help = "Create a user and generate an API key for a scan queue worker"

    def handle(self, *args, **options):
        super().handle(**options)
        username = options["username"]
        user = self.UserModel._default_manager.get(username=username)

        # Add user to `scan_queue_workers` group
        scan_queue_workers_group, _ = Group.objects.get_or_create(name="scan_queue_workers")
        scan_queue_workers_group.user_set.add(user)
        msg = f"User {username} added to `scan_queue_workers` group"
        self.stdout.write(msg, self.style.SUCCESS)
