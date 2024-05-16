#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from commoncode.fileutils import delete

from minecode.indexing import index_package
from minecode.models import ScannableURI


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

    `scan_results_location` and `scan_summary_location` are deleted after the
    indexing process has finished.
    """

    with open(scan_results_location) as f:
        scan_data = json.load(f)
    with open(scan_summary_location) as f:
        summary_data = json.load(f)
    project_extra_data = json.loads(project_extra_data)

    try:
        scannable_uri = ScannableURI.objects.get(uuid=scannable_uri_uuid)
    except ScannableURI.DoesNotExist:
        raise Exception(f'ScannableURI {scannable_uri_uuid} does not exist!')

    indexing_errors = index_package(
        scannable_uri,
        scannable_uri.package,
        scan_data,
        summary_data,
        project_extra_data,
        reindex=scannable_uri.reindex_uri,
    )

    if indexing_errors:
        scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
        scannable_uri.index_error = indexing_errors
    else:
        scannable_uri.scan_status = ScannableURI.SCAN_INDEXED

    scannable_uri.wip_date = None
    scannable_uri.save()

    # Clean up after indexing has ended
    delete(scan_results_location)
    delete(scan_summary_location)
