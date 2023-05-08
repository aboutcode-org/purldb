#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from packageurl import PackageURL

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.models import ResourceURI
from minecode.models import PriorityResourceURI


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

    @action(detail=False, methods=["post"])
    def add_to_queue(self, request, *args, **kwargs):
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
                'status': f'purl {purl} cannot be fetched: no route available for Package of type: {package_url.type}'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # add to queue
        PriorityResourceURI.objects.create(uri=purl, package_url=purl)

        message = {
            'status': f'purl {purl} added to queue'
        }
        return Response(message)
