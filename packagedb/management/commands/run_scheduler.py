#
# Copyright (c) nexB Inc. and others. All rights reserved.
# PurlDB is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django_rq.management.commands import rqscheduler

from packagedb.models import PackageWatch
from packagedb.schedules import clear_zombie_watch_schedules
from packagedb.schedules import scheduled_job_exists


def init_watch_scheduled():
    """Initialize scheduled jobs for active PackageWatch."""
    active_watch_qs = PackageWatch.objects.filter(is_active=True)
    for watch in active_watch_qs:
        if scheduled_job_exists(watch.schedule_work_id):
            continue
        new_id = watch.create_new_job()
        watch.schedule_work_id = new_id
        watch.save(update_fields=["schedule_work_id"])


class Command(rqscheduler.Command):
    def handle(self, *args, **kwargs):
        clear_zombie_watch_schedules()
        init_watch_scheduled()
        super().handle(*args, **kwargs)
