#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from packageurl import PackageURL
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

# UnusedImport here!
# But importing the collectors module triggers routes registration
from minecode import collectors  # NOQA
from minecode import priority_router
from minecode.models import PriorityResourceURI
from minecode.models import ResourceURI
from minecode.models import ScannableURI
from minecode.permissions import IsScanQueueWorkerAPIUser
from minecode.utils import get_temp_file
from minecode.utils import get_webhook_url


class ResourceURISerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceURI


class ResourceURIViewSet(viewsets.ModelViewSet):
    queryset = ResourceURI.objects.all()
    serializer_class = ResourceURISerializer
    paginate_by = 10


class PriorityResourceURISerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityResourceURI
        fields = "__all__"


class PriorityResourceURIViewSet(viewsets.ModelViewSet):
    queryset = PriorityResourceURI.objects.all()
    serializer_class = PriorityResourceURISerializer
    paginate_by = 10

    # TODO: hide fact that this is a queue, do not show queue contents (hide from view)
    # TODO: hide debug endpoints under `admin`
    @action(detail=False, methods=["post"])
    def index_package(self, request, *args, **kwargs):
        """Request the indexing and scanning of Package, given a valid Package URL `purl`."""
        purl = request.data.get("purl")

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
        except ValueError as e:
            message = {"status": f"purl validation error: {e}"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # see if its routeable
        if not priority_router.is_routable(purl):
            message = {"status": f"Package type `{package_url.type}` is unsupported"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # add to queue
        priority_resource_uri = PriorityResourceURI.objects.insert(uri=purl)

        if priority_resource_uri:
            message = {
                "status": f"Package index request for {purl} has been successful."
            }
        else:
            message = {
                "status": f"Package {purl} has already been requested for indexing."
            }
        # TODO: revisiting a package should be handled on another level, dependent on data we store
        return Response(message)


class ScannableURISerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannableURI
        fields = "__all__"


class ScannableURIViewSet(viewsets.ModelViewSet):
    queryset = ScannableURI.objects.all()
    serializer_class = ScannableURISerializer
    permission_classes = [IsScanQueueWorkerAPIUser | IsAdminUser]
    lookup_field = "uuid"

    @action(detail=False, methods=["get"])
    def get_next_download_url(self, request, *args, **kwargs):
        """Return download url for next Package on scan queue"""
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_scannable()
            if scannable_uri:
                user = self.request.user
                webhook_url = get_webhook_url("index_package_scan", user.id)
                response = {
                    "scannable_uri_uuid": scannable_uri.uuid,
                    "download_url": scannable_uri.uri,
                    "pipelines": scannable_uri.pipelines,
                    "webhook_url": webhook_url,
                }
                scannable_uri.scan_status = ScannableURI.SCAN_SUBMITTED
                scannable_uri.scan_date = timezone.now()
                scannable_uri.save()
            else:
                response = {
                    "scannable_uri_uuid": "",
                    "download_url": "",
                    "pipelines": [],
                    "webhook_url": "",
                }
            return Response(response)

    @action(detail=True, methods=["post"])
    def update_status(self, request, *args, **kwargs):
        """
        Update the status of a ScannableURI with `scan_status`

        If `scan_status` is 'failed', then a `scan_log` string is expected and
        should contain the error messages for that scan.
        """
        scan_status = request.data.get("scan_status")
        if not scan_status:
            response = {"error": "missing scan_status"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        scannable_uri = self.get_object()
        scannable_uri_uuid = scannable_uri.uuid
        scannable_uri_status = ScannableURI.SCAN_STATUSES_BY_CODE.get(
            scannable_uri.scan_status
        )

        if scannable_uri.scan_status in [
            ScannableURI.SCAN_INDEXED,
            ScannableURI.SCAN_FAILED,
            ScannableURI.SCAN_TIMEOUT,
            ScannableURI.SCAN_INDEX_FAILED,
        ]:
            response = {
                "error": f"cannot update status for scannable_uri {scannable_uri_uuid}: "
                f'scannable_uri has finished with status "{scannable_uri_status}"'
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if scan_status == scannable_uri_status:
            response = {
                "error": f"cannot update status for scannable_uri {scannable_uri_uuid}: "
                f'scannable_uri status is already "{scannable_uri_status}"'
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if scan_status == "failed":
            scan_log = request.data.get("scan_log")
            scannable_uri.scan_error = scan_log
            scannable_uri.scan_status = ScannableURI.SCAN_FAILED
            scannable_uri.wip_date = None
            scannable_uri.save()
            response = {
                "status": f"updated scannable_uri {scannable_uri_uuid} scan_status to {scan_status}"
            }
            return Response(response)

        response = {"error": f"invalid scan_status: {scan_status}"}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


@require_POST
@csrf_exempt
def index_package_scan(request, key):
    """
    Given a `request` to the `/api/scan_queue/index_package_scan/<key>/`
    endpoint, where `key` is the id of the purldb scan queue worker that has
    been encoded as a secret, save the package scan results and summary to files
    and create a new rq worker task to index the scan results and summary.
    """
    try:
        json_data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        raise Http404

    user_id = signing.loads(key)
    User = get_user_model()
    get_object_or_404(User, id=user_id)

    results = json_data.get("results")
    summary = json_data.get("summary")
    project_data = json_data.get("project")
    extra_data = project_data.get("extra_data")
    scannable_uri_uuid = extra_data.get("scannable_uri_uuid")

    # Save results to temporary files
    scan_results_location = get_temp_file(file_name="scan_results", extension=".json")
    scan_summary_location = get_temp_file(file_name="scan_summary", extension=".json")

    with open(scan_results_location, "w") as f:
        json.dump(results, f)

    with open(scan_summary_location, "w") as f:
        json.dump(summary, f)

    scannable_uri = get_object_or_404(ScannableURI, uuid=scannable_uri_uuid)
    scannable_uri.process_scan_results(
        scan_results_location=scan_results_location,
        scan_summary_location=scan_summary_location,
        project_extra_data=extra_data,
    )
    msg = {
        "status": f"scan results for scannable_uri {scannable_uri.uuid} "
        "have been queued for indexing"
    }
    return JsonResponse(msg)
