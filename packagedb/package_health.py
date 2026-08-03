#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import timedelta

from django.utils import timezone
from fetchcode.package import info

from packagedb.models import PackageHealthMetrics

HEALTH_METRICS_MAX_AGE = timedelta(days=7)


def get_fresh_health_metrics(package):
    """
    Return the most recent PackageHealthMetrics for `package` if it is no
    older than HEALTH_METRICS_MAX_AGE, otherwise return None.
    """
    cutoff = timezone.now() - HEALTH_METRICS_MAX_AGE
    return (
        package.health_metrics.filter(creation_date__gte=cutoff).order_by("-creation_date").first()
    )


def get_repo_url_from_fetchcode(purl):
    """
    Return the repository VCS URL for `purl` using fetchcode.

    Return None if fetchcode cannot resolve the package or no VCS URL is found.
    """
    try:
        packages = [p for p in info(str(purl)) or []]
    except Exception:
        return None

    if not packages:
        return None

    return packages[0].vcs_url or None


def run_scio_health_pipeline(repo_url):
    """
    Run the SCIO health-metrics pipeline for `repo_url` and return metrics.

    The SCIO pipeline does not exist yet. This stub returns a placeholder
    mapping so callers can store results in PackageHealthMetrics.
    """
    # TODO: Replace with a real SCIO pipeline invocation when available.
    return {
        "repo_url": repo_url,
        "score": None,
        "status": "pending_scio_pipeline",
        "note": "SCIO health pipeline is not implemented; placeholder metrics.",
    }


def fetch_and_store_health_metrics(package, purl):
    """
    Fetch health metrics for `package` via fetchcode + SCIO and store them.

    Return a tuple of (PackageHealthMetrics, error_message).
    On success, error_message is None. On failure, PackageHealthMetrics is None.
    """
    repo_url = get_repo_url_from_fetchcode(purl)
    if not repo_url:
        return None, f"Could not determine repository URL for {purl} via fetchcode."

    metrics = run_scio_health_pipeline(repo_url)
    health_metrics = PackageHealthMetrics.objects.create(
        package=package,
        metrics=metrics,
    )
    return health_metrics, None
