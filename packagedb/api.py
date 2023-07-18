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
import django_filters

from packageurl import PackageURL
from packageurl.contrib.django.utils import purl_to_lookups
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from matchcode.api import MultipleCharFilter
from matchcode.api import MultipleCharInFilter
# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.models import PriorityResourceURI
from minecode.route import NoRouteAvailable
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet
from packagedb.models import Resource
from packagedb.serializers import DependentPackageSerializer
from packagedb.serializers import ResourceAPISerializer
from packagedb.serializers import PackageAPISerializer
from packagedb.serializers import PackageSetAPISerializer
from packagedb.serializers import PartySerializer

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
    md5 = MultipleCharInFilter(
        help_text="Exact MD5. Multi-value supported.",
    )
    sha1 = MultipleCharInFilter(
        help_text="Exact SHA1. Multi-value supported.",
    )


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Resource.objects.select_related('package')
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
    type = django_filters.CharFilter(
        lookup_expr="iexact",
        help_text="Exact type. (case-insensitive)",
    )
    namespace = django_filters.CharFilter(
        lookup_expr="iexact",
        help_text="Exact namespace. (case-insensitive)",
    )
    name = MultipleCharFilter(
        lookup_expr="iexact",
        help_text="Exact name. Multi-value supported. (case-insensitive)",
    )
    version = MultipleCharFilter(
        help_text="Exact version. Multi-value supported.",
    )
    md5 = MultipleCharInFilter(
        help_text="Exact MD5. Multi-value supported.",
    )
    sha1 = MultipleCharInFilter(
        help_text="Exact SHA1. Multi-value supported.",
    )
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
    queryset = Package.objects.prefetch_related('dependencies', 'parties')
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

    @action(detail=False)
    def get_package(self, request, *args, **kwargs):
        purl = request.query_params.get('purl')

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
        except ValueError as e:
            message = {
                'status': f'purl validation error: {e}'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        lookups = purl_to_lookups(purl)
        packages = Package.objects.filter(**lookups)
        if packages.count() == 0:
            # add to queue
            PriorityResourceURI.objects.insert(purl)
            return Response({})

        serializer = PackageAPISerializer(packages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False)
    def get_or_fetch_package(self, request, *args, **kwargs):
        """
        Return Package data for the purl passed in the `purl` query parameter.

        If the package does not exist, we will fetch the Package data and return
        it in the same request.
        """
        purl = request.query_params.get('purl')

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
        except ValueError as e:
            message = {
                'status': f'purl validation error: {e}'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        lookups = purl_to_lookups(purl)
        packages = Package.objects.filter(**lookups)
        if packages.count() == 0:
            try:
                errors = priority_router.process(purl)
            except NoRouteAvailable:
                message = {
                    'status': f'cannot fetch Package data for {purl}: no available handler'
                }
                return Response(message, status=status.HTTP_400_BAD_REQUEST)

            lookups = purl_to_lookups(purl)
            packages = Package.objects.filter(**lookups)
            if packages.count() == 0:
                message = {}
                if errors:
                    message = {
                        'status': f'error(s) occured when fetching metadata for {purl}: {errors}'
                    }
                return Response(message)

        serializer = PackageAPISerializer(packages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def get_enhanced_package_data(self, request, *args, **kwargs):
        """
        Return a mapping of enhanced Package data for a given Package
        """
        package = self.get_object()
        package_data = get_enhanced_package(package)
        return Response(package_data)


UPDATEABLE_FIELDS = [
    'primary_language',
    'copyright',

    'declared_license_expression',
    'declared_license_expression_spdx',
    'license_detections',
    'other_license_expression',
    'other_license_expression_spdx',
    'other_license_detections',
    # TODO: update extracted license statement and other fields together
    # all license fields are based off of `extracted_license_statement` and should be treated as a unit
    # hold off for now
    'extracted_license_statement',

    'notice_text',
    'api_data_url',
    'bug_tracking_url',
    'code_view_url',
    'vcs_url',
    'source_packages',
    'repository_homepage_url',
    'dependencies',
    'parties',
    'homepage_url',
    'description',
]


NONUPDATEABLE_FIELDS = [
    'type',
    'namespace',
    'name',
    'version',
    'qualifiers',
    'subpath',
    'purl',
    'datasource_id',
    'download_url',
    'size',
    'md5',
    'sha1',
    'sha256',
    'sha512',
    'package_uid',
    'repository_download_url',
    'file_references',
    'history',
    # TODO: add in history fields, last modified date, etc.
    #
]


def get_enhanced_package(package):
    """
    Return package data from `package`, where the data has been enhanced by
    other packages in the same package_set.
    """
    package_content = package.package_content
    if package_content == PackageContentType.SOURCE_REPO:
        # Source repo packages can't really be enhanced much further, datawise
        return package.to_dict()
    if package_content in [PackageContentType.BINARY, PackageContentType.SOURCE_ARCHIVE]:
        # Binary packages can only be part of one set
        # TODO: Can source_archive packages be part of multiple sets?
        package_set = package.package_sets.first()
        if package_set:
            package_set_members = package_set.get_package_set_members()
            if package_content == PackageContentType.SOURCE_ARCHIVE:
                # Mix data from SOURCE_REPO packages for SOURCE_ARCHIVE packages
                package_set_members = package_set_members.filter(
                    package_content=PackageContentType.SOURCE_REPO
                )
            # TODO: consider putting in the history field that we enhanced the data
            return _get_enhanced_package(package, package_set_members)
        else:
            return package.to_dict()


def _get_enhanced_package(package, packages):
    """
    Return a mapping of package data based on `package` and Packages in
    `packages`.
    """
    mixing = False
    package_data = {}
    for peer in packages:
        if peer == package:
            mixing = True
            package_data = package.to_dict()
            continue
        if not mixing:
            continue
        if peer.package_content == package.package_content:
            # We do not want to mix data with peers of the same package content
            continue
        enhanced = False
        for field in UPDATEABLE_FIELDS:
            package_value = package_data.get(field)
            peer_value = getattr(peer, field)
            if not package_value and peer_value:
                if field == 'parties':
                    peer_value = PartySerializer(peer_value, many=True).data
                if field == 'dependencies':
                    peer_value = DependentPackageSerializer(peer_value, many=True).data
                package_data[field] = peer_value
                enhanced = True
        if enhanced:
            extra_data = package_data.get('extra_data', {})
            enhanced_by = extra_data.get('enhanced_by', [])
            enhanced_by.append(peer.purl)
            extra_data['enhanced_by'] = enhanced_by
            package_data['extra_data'] = extra_data
    return package_data


class PackageSetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PackageSet.objects.prefetch_related('packages')
    serializer_class = PackageSetAPISerializer
