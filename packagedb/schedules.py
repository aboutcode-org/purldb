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
from redis.exceptions import ConnectionError

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

    job = scheduler.schedule(
        scheduled_time=first_execution,
        func=watch_new_purls,
        args=[watch.package_url],
        interval=interval_in_seconds,
        result_ttl=interval_in_seconds,  # Remove job results after next run
        repeat=None,  # None means repeat forever
    )
    return job._id


def clear_job(job):
    scheduler.cancel(job)


def scheduled_job_exists(job_id):
    return job_id and (job_id in scheduler)


def clear_zombie_watch_schedules():
    from packagedb.models import PackageWatch
    schedule_ids = PackageWatch.objects.all().values_list("schedule_work_id", flat=True)
    
    for job in scheduler.get_jobs():
        if job._id not in schedule_ids:
            log.debug(f"Deleting scheduled job {job}")
            clear_job(job)


def is_redis_running():
    try:
        connection =django_rq.get_connection()
        return connection.ping()
    except ConnectionError as e:
        error_message = f"Error checking Redis status: {e}. Redis is not reachable."
        log.error(error_message)
        return False
