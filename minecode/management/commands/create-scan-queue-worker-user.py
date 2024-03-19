#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.contrib.auth.models import Group
from minecode.management.user_creation import CreateUserCommand


class Command(CreateUserCommand):
    help = 'Create a user and generate an API key for a scan queue worker'

    def handle(self, *args, **options):
        username = options['username']
        interactive = options['interactive']
        verbosity = options['verbosity']
        user = self.create_user(
            username=username,
            interactive=interactive,
            verbosity=verbosity
        )
        # Add user to `scan_queue_workers` group
        scan_queue_workers_group, _ = Group.objects.get_or_create(name='scan_queue_workers')
        scan_queue_workers_group.user_set.add(user)
        msg = f'User {username} added to `scan_queue_workers` group'
        self.stdout.write(msg, self.style.SUCCESS)
