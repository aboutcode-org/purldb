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
from packageurl import PackageURL
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.management.commands.process_scans import index_package_files
from minecode.models import PriorityResourceURI, ResourceURI, ScannableURI


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


# TODO: guard these API endpoints behind an API key
class ScannableURIViewSet(viewsets.ModelViewSet):
    queryset = ScannableURI.objects.all()
    serializer_class = ScannableURISerializer

    @action(detail=False, methods=["get"])
    def get_next_download_url(self, request, *args, **kwargs):
        """
        Return download url for next Package on scan queue
        """
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_scannable()
            if scannable_uri:
                response = {
                    'package_uuid': scannable_uri.package.uuid,
                    'download_url': scannable_uri.uri,
                }
                scannable_uri.scan_status = ScannableURI.SCAN_SUBMITTED
                scannable_uri.save()
            else:
                response = {
                    'message': 'no more packages on scan queue'
                }
            return Response(response)

    @action(detail=False, methods=["post"])
    def submit_scan_results(self, request, *args, **kwargs):
        """
        Receive and index completed scan
        """
        from packagedb.models import Package

        package_uuid = request.data.get('package_uuid')
        scan_file = request.data.get('scan_file')

        missing = []
        if not package_uuid:
            missing.append('package_uuid')
        if not scan_file:
            missing.append('scan_file')
        if missing:
            msg = ', '.join(missing)
            response = {
                'error': f'missing {msg}'
            }
            return Response(response)

        package = Package.objects.get(uuid=package_uuid)
        scan_data= json.load(scan_file)
        indexing_errors = index_package_files(package, scan_data, reindex=True)
        if indexing_errors:
            return Response({'error': f'indexing errors:\n\n{indexing_errors}'})
        return Response({'message': 'success'})
