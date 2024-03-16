#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.db import transaction
from django.utils import timezone
from packageurl import PackageURL
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.management.indexing import index_package
from minecode.models import PriorityResourceURI, ResourceURI, ScannableURI
from minecode.permissions import IsScanQueueWorkerAPIUser


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
        fields = '__all__'


class PriorityResourceURIViewSet(viewsets.ModelViewSet):
    queryset = PriorityResourceURI.objects.all()
    serializer_class = PriorityResourceURISerializer
    paginate_by = 10

    # TODO: hide fact that this is a queue, do not show queue contents (hide from view)
    # TODO: hide debug endpoints under `admin`
    @action(detail=False, methods=["post"])
    def index_package(self, request, *args, **kwargs):
        """
        Request the indexing and scanning of Package, given a valid Package URL `purl`.
        """
        purl = request.data.get('purl')

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
        except ValueError as e:
            message = {
                'status': f'purl validation error: {e}'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # see if its routeable
        if not priority_router.is_routable(purl):
            message = {
                'status': f'Package type `{package_url.type}` is unsupported'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # add to queue
        priority_resource_uri = PriorityResourceURI.objects.insert(uri=purl)

        if priority_resource_uri:
            message = {
                'status': f'Package index request for {purl} has been successful.'
            }
        else:
            message = {
                'status': f'Package {purl} has already been requested for indexing.'
            }
        # TODO: revisiting a package should be handled on another level, dependent on data we store
        return Response(message)


class ScannableURISerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannableURI
        fields = '__all__'


class ScannableURIViewSet(viewsets.ModelViewSet):
    queryset = ScannableURI.objects.all()
    serializer_class = ScannableURISerializer
    permission_classes = [IsScanQueueWorkerAPIUser]

    @action(detail=False, methods=["get"])
    def get_next_download_url(self, request, *args, **kwargs):
        """
        Return download url for next Package on scan queue
        """
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_scannable()
            if scannable_uri:
                response = {
                    'scannable_uri_uuid': scannable_uri.uuid,
                    'download_url': scannable_uri.uri,
                    'pipelines': scannable_uri.pipelines,
                }
                scannable_uri.scan_status = ScannableURI.SCAN_SUBMITTED
                scannable_uri.scan_date = timezone.now()
                scannable_uri.save()
            else:
                response = {
                    'scannable_uri_uuid': "",
                    'download_url': "",
                    'pipelines': [],
                }
            return Response(response)

    @action(detail=False, methods=["post"])
    def update_status(self, request, *args, **kwargs):
        scannable_uri_uuid = request.data.get('scannable_uri_uuid')
        scan_status = request.data.get('scan_status')
        if not scannable_uri_uuid:
            response = {
                'error': 'missing scannable_uri_uuid'
            }
            return Response(response)

        scannable_uri = ScannableURI.objects.get(uuid=scannable_uri_uuid)

        if scan_status == 'failed':
            scan_log = request.data.get('scan_log')
            scannable_uri.scan_error = scan_log
            scannable_uri.scan_status = ScannableURI.SCAN_FAILED
            scannable_uri.wip_date = None
            scannable_uri.save()
            msg = {
                'status': f'updated scannable uri {scannable_uri_uuid} scan_status to {scan_status}'
            }

        elif scan_status == 'scanned':
            scan_results_file = request.data.get('scan_results_file')
            scan_summary_file = request.data.get('scan_summary_file')
            project_extra_data = request.data.get('project_extra_data')
            scannable_uri.scan_status = ScannableURI.SCAN_COMPLETED
            package = scannable_uri.package
            scan_data = json.load(scan_results_file)
            summary_data = json.load(scan_summary_file)
            project_extra_data = json.loads(project_extra_data)
            indexing_errors = index_package(
                scannable_uri,
                package,
                scan_data,
                summary_data,
                project_extra_data,
                reindex=True
            )
            if indexing_errors:
                scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
                scannable_uri.index_error = indexing_errors
                msg = {
                    'status': f'scan index failed for scannable uri {scannable_uri_uuid}'
                }
            else:
                scannable_uri.scan_status = ScannableURI.SCAN_INDEXED
                msg = {
                    'status': f'scan indexed for scannable uri {scannable_uri_uuid}'
                }
            scannable_uri.wip_date = None
            scannable_uri.save()

        else:
            msg = {
                'status': f'invalid scan_status: {scan_status}'
            }

        return Response(msg)
