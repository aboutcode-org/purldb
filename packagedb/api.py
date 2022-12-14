#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.core.exceptions import ValidationError
from django.db.models import Q
from django_filters.rest_framework import FilterSet
from django_filters.filters import Filter
from django_filters.filters import OrderingFilter

from packageurl.contrib.django.utils import purl_to_lookups
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from packagedb.models import Package
from packagedb.models import Resource
from packagedb.serializers import PackageAPISerializer
from packagedb.serializers import ResourceAPISerializer


class PackageResourcePurlFilter(Filter):
    def filter(self, qs, value):
        if not value:
            return qs

        lookups = purl_to_lookups(value)
        if not lookups:
            return qs

        try:
            package = Package.objects.get(**lookups)
        except Package.DoesNotExist:
            return qs.none()

        return qs.filter(package=package)


class PackageResourceUUIDFilter(Filter):
    def filter(self, qs, value):
        if not value:
            return qs

        try:
            package = Package.objects.get(uuid=value)
        except (Package.DoesNotExist, ValidationError) as e:
            return qs.none()

        return qs.filter(package=package)


class ResourceFilter(FilterSet):
    package = PackageResourceUUIDFilter(label='Package UUID')
    purl = PackageResourcePurlFilter(label='Package pURL')


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceAPISerializer
    filterset_class = ResourceFilter
    lookup_field = 'sha1'


class MultiplePackageURLFilter(Filter):
    def filter(self, qs, value):
        try:
            request = self.parent.request
        except AttributeError:
            return None

        values = request.GET.getlist(self.field_name)
        if all(v == '' for v in values):
            return qs

        values = {item for item in values}

        q = Q()
        for val in values:
            lookups = purl_to_lookups(val)
            if not lookups:
                continue

            q.add(Q(**lookups), Q.OR)

        if not q:
            return qs.none()

        return qs.filter(q)


class PackageSearchFilter(Filter):
    def filter(self, qs, value):
        try:
            request = self.parent.request
        except AttributeError:
            return None

        if not value:
            return qs

        return Package.objects.filter(search_vector=value)


class PackageFilter(FilterSet):
    purl = MultiplePackageURLFilter(label='Package URL')
    search = PackageSearchFilter(label='Search')

    sort = OrderingFilter(fields=[
            'type',
            'namespace',
            'name',
            'version',
            'qualifiers',
            'subpath',
            'download_url',
            'filename',
            'size',
            'release_date'
    ])

    class Meta:
        model = Package
        fields = (
            'type',
            'namespace',
            'name',
            'version',
            'qualifiers',
            'subpath',
            'download_url',
            'filename',
            'sha1',
            'sha256',
            'md5',
            'size',
            'release_date',
        )


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageAPISerializer
    lookup_field = 'uuid'
    filterset_class = PackageFilter

    @action(detail=True, methods=['get'])
    def latest_version(self, request, *args, **kwargs):
        """
        Return the latest version of the current Package,
        which can be itself if current is the latest.
        """
        package = self.get_object()

        latest_version = package.get_latest_version()
        if latest_version:
            return Response(
                PackageAPISerializer(latest_version, context={'request': request}).data
            )

        return Response({})

    @action(detail=True, methods=['get'])
    def resources(self, request, *args, **kwargs):
        """
        Return the Resources associated with the current Package.
        """
        package = self.get_object()

        qs = Resource.objects.filter(package=package)
        paginated_qs = self.paginate_queryset(qs)

        serializer = ResourceAPISerializer(paginated_qs, many=True, context={'request': request})
        return Response(serializer.data)
