#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import datetime
import logging

import django_rq
from redis.exceptions import ConnectionError

from packagedb.tasks import watch_new_packages

log = logging.getLogger(__name__)
scheduler = django_rq.get_scheduler()


def get_next_execution(watch_interval_days, last_watch_date):
    """Calculate the next execution time based on the watch_interval_days and last_watch_date."""
    current_date_time = datetime.datetime.now(tz=datetime.timezone.utc)
    if last_watch_date:
        next_execution = last_watch_date + datetime.timedelta(days=watch_interval_days)
        if next_execution > current_date_time:
            return next_execution

    return current_date_time


def schedule_watch(watch):
    """
    Takes a `PackageWatch` object as input and schedule a
    recurring job using `rq_scheduler` to watch the package.
    """
    watch_interval = watch.watch_interval
    last_watch_date = watch.last_watch_date

    first_execution = get_next_execution(watch_interval, last_watch_date)
    interval_in_seconds = watch_interval * 24 * 60 * 60

    job = scheduler.schedule(
        scheduled_time=first_execution,
        func=watch_new_packages,
        args=[watch.package_url],
        interval=interval_in_seconds,
        result_ttl=interval_in_seconds,  # Remove job results after next run
        repeat=None,  # None means repeat forever
    )
    return job._id


def clear_job(job):
    """
    Take a job object or job ID as input
    and cancel the corresponding scheduled job.
    """
    return scheduler.cancel(job)


def scheduled_job_exists(job_id):
    """Check if a scheduled job with the given job ID exists."""
    return job_id and (job_id in scheduler)


def clear_zombie_watch_schedules(logger=log):
    """Clear scheduled jobs not associated with any PackageWatch object."""
    from packagedb.models import PackageWatch

    schedule_ids = PackageWatch.objects.all().values_list("schedule_work_id", flat=True)

    for job in scheduler.get_jobs():
        if job._id not in schedule_ids:
            logger.info(f"Deleting scheduled job {job}")
            clear_job(job)


def is_redis_running(logger=log):
    """Check the status of the Redis server."""
    try:
        connection = django_rq.get_connection()
        return connection.ping()
    except ConnectionError as e:
        error_message = f"Error checking Redis status: {e}. Redis is not reachable."
        log.error(error_message)
        return False
