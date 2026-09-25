#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging

from commoncode.fileutils import delete

from minecode.indexing import index_package
from minecode.models import ScannableURI

logger = logging.getLogger(__name__)


def process_scan_results(
    scannable_uri_uuid,
    scan_results_location,
    scan_summary_location,
    project_extra_data,
):
    """
    Indexes the scan results from `scan_results_location`,
    `scan_summary_location`, and `project_extra_data` for the Package related to
    ScannableURI with UUID `scannable_uri_uuid`.

    When the ScannableURI pipelines include ``scan_repo_health``, also write
    PackageHealthMetrics for the related Package.

    `scan_results_location` and `scan_summary_location` are deleted after the
    indexing process has finished.
    """
    from packagedb.package_health import HEALTH_METRICS_PIPELINE
    from packagedb.package_health import write_package_health_metrics

    with open(scan_results_location) as f:
        scan_data = json.load(f)
    with open(scan_summary_location) as f:
        summary_data = json.load(f)
    if not isinstance(scan_data, dict):
        scan_data = {}
    if not isinstance(summary_data, dict):
        summary_data = {}
    if not isinstance(project_extra_data, dict):
        try:
            project_extra_data = json.loads(project_extra_data) if project_extra_data else {}
        except (TypeError, json.JSONDecodeError):
            project_extra_data = {}

    try:
        scannable_uri = ScannableURI.objects.get(uuid=scannable_uri_uuid)
    except ScannableURI.DoesNotExist:
        raise Exception(f"ScannableURI {scannable_uri_uuid} does not exist!")

    pipelines = scannable_uri.pipelines or []
    is_health_scan = HEALTH_METRICS_PIPELINE in pipelines
    health_only = is_health_scan and list(pipelines) == [HEALTH_METRICS_PIPELINE]

    indexing_errors = None
    if not health_only:
        indexing_errors = index_package(
            scannable_uri,
            scannable_uri.package,
            scan_data,
            summary_data,
            project_extra_data,
            reindex=scannable_uri.reindex_uri,
        )

    scannable_uri.refresh_from_db()

    health_row = None
    if is_health_scan:
        health_row = write_package_health_metrics(
            package=scannable_uri.package,
            project_extra_data=project_extra_data,
        )
        if health_row is None:
            logger.warning(
                "scan_repo_health finished for %s but no metrics in "
                "project_extra_data keys=%s — ScanCode.io likely failed "
                "format_metrics_output before updating project.extra_data "
                "(check the ScanCode.io run log for that project)",
                scannable_uri_uuid,
                sorted(project_extra_data.keys()),
            )

    if health_only:
        if health_row:
            scannable_uri.scan_status = ScannableURI.SCAN_INDEXED
        else:
            scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
            scannable_uri.index_error = (
                scannable_uri.index_error or "Health metrics payload missing from scan results"
            )
    elif indexing_errors or scannable_uri.scan_status == ScannableURI.SCAN_INDEX_FAILED:
        scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
        if indexing_errors:
            scannable_uri.index_error = indexing_errors
    else:
        scannable_uri.scan_status = ScannableURI.SCAN_INDEXED

    scannable_uri.wip_date = None
    scannable_uri.save()

    # Clean up after indexing has ended
    delete(scan_results_location)
    delete(scan_summary_location)
