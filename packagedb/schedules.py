#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import datetime
import logging

import django_rq
from packagedb.tasks import watch_new_purls

log = logging.getLogger(__name__)
scheduler = django_rq.get_scheduler()


def schedule_watch(watch):
    watch_interval = watch.watch_interval
    last_watch_date = watch.last_watch_date

    first_execution = datetime.datetime.now(tz=datetime.timezone.utc)
    if last_watch_date:
        next_watch_time = last_watch_date + datetime.timedelta(days=watch_interval)
        if next_watch_time > first_execution:
            first_execution = next_watch_time

    interval_in_seconds = watch_interval * 24 * 60 * 60

    # Debug
    # interval_in_seconds = 60
    # first_execution = datetime.datetime.now(tz=datetime.timezone.utc)
    job = scheduler.schedule(
        scheduled_time=first_execution,
        func=watch_new_purls,
        args=[watch.package_url],
        interval=interval_in_seconds,
        # Enable in prod
        # result_ttl=interval_in_seconds,  # Remove job results after next run
        repeat=None,  # None means repeat forever
    )
    return job._id


def clear_job(job):
    scheduler.cancel(job)


def clear_scheduled_jobs():
    # Delete all scheduled jobs
    for job in scheduler.get_jobs():
        log.debug(f"Deleting scheduled job {job}")
        clear_job(job)


def clear_scheduled_jobs():
    # Delete all scheduled jobs
    for job in scheduler.get_jobs():
        log.debug(f"Deleting scheduled job {job}")
        clear_job(job)


def scheduled_job_exists(job_id):
    return job_id and (job_id in scheduler)
