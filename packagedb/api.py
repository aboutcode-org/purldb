#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging

import django_filters
from django.core.exceptions import ValidationError
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django_filters.filters import Filter
from django_filters.filters import OrderingFilter
from django_filters.rest_framework import FilterSet
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from packageurl import PackageURL
from packageurl.contrib.django.utils import purl_to_lookups
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from univers.version_constraint import InvalidConstraintsError
from univers.version_range import RANGE_CLASS_BY_SCHEMES
from univers.version_range import VersionRange
from univers.versions import InvalidVersion

from matchcode.api import MultipleCharFilter
from matchcode.api import MultipleCharInFilter
# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import priority_router
from minecode import visitors  # NOQA
from minecode.models import PriorityResourceURI
from minecode.models import ScannableURI
from minecode.route import NoRouteAvailable
from packagedb.filters import PackageSearchFilter
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet
from packagedb.models import PackageWatch
from packagedb.models import Resource
from packagedb.package_managers import VERSION_API_CLASSES_BY_PACKAGE_TYPE
from packagedb.package_managers import get_api_package_name
from packagedb.package_managers import get_version_fetcher
from packagedb.serializers import DependentPackageSerializer
from packagedb.serializers import IndexPackagesResponseSerializer
from packagedb.serializers import IndexPackagesSerializer
from packagedb.serializers import PackageAPISerializer
from packagedb.serializers import PackageSetAPISerializer
from packagedb.serializers import PackageWatchAPISerializer
from packagedb.serializers import PackageWatchCreateSerializer
from packagedb.serializers import PackageWatchUpdateSerializer
from packagedb.serializers import PartySerializer
from packagedb.serializers import PurlValidateResponseSerializer
from packagedb.serializers import PurlValidateSerializer
from packagedb.serializers import ResourceAPISerializer
from packagedb.throttling import StaffUserRateThrottle

logger = logging.getLogger(__name__)


class CreateListRetrieveUpdateViewSetMixin(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `create`, `list, `retrieve`, and `update` actions.
    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """
    pass


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


class ResourceFilterSet(FilterSet):
    package = PackageResourceUUIDFilter(label='Package UUID')
    purl = PackageResourcePurlFilter(label='Package pURL')
    md5 = MultipleCharInFilter(
        help_text='Exact MD5. Multi-value supported.',
    )
    sha1 = MultipleCharInFilter(
        help_text='Exact SHA1. Multi-value supported.',
    )


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Resource.objects.select_related('package')
    serializer_class = ResourceAPISerializer
    filterset_class = ResourceFilterSet
    throttle_classes = [StaffUserRateThrottle, AnonRateThrottle]
    lookup_field = 'sha1'

    @action(detail=False, methods=['post'])
    def filter_by_checksums(self, request, *args, **kwargs):
        """
        Take a mapping, where the keys are the names of the checksum algorthm
        and the values is a list of checksum values and query those values
        against the packagedb.

        Supported checksum fields are:

        - md5
        - sha1

        Example:

            {
                "sha1": [
                    "b55fd82f80cc1bd0bdabf9c6e3153788d35d7911",
                    "27afff2610b5a94274a2311f8b15e514446b0e76
                ]
            }

        Multiple checksums algorithms can be passed together:

            {
                "sha1": [
                    "b55fd82f80cc1bd0bdabf9c6e3153788d35d7911",
                    "27afff2610b5a94274a2311f8b15e514446b0e76
                ],
                "md5": [
                    "e927df60b093456d4e611ae235c1aa5b"
                ]
            }

        This will return Resources whose sha1 or md5 matches those values.
        """
        data = dict(request.data)
        unsupported_fields = []
        for field, value in data.items():
            if field not in ('md5', 'sha1'):
                unsupported_fields.append(field)

        if unsupported_fields:
            unsupported_fields_str = ', '.join(unsupported_fields)
            response_data = {
                'status': f'Unsupported field(s) given: {unsupported_fields_str}'
            }
            return Response(response_data)

        if not data:
            response_data = {
                'status': 'No values provided'
            }
            return Response(response_data)

        lookups = Q()
        for field, value in data.items():
            value = value or []
            # We create this intermediate dictionary so we can modify the field
            # name to have __in at the end
            d = {f'{field}__in': value}
            lookups |= Q(**d)

        qs = Resource.objects.filter(lookups)
        paginated_qs = self.paginate_queryset(qs)
        serializer = ResourceAPISerializer(paginated_qs, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class MultiplePackageURLFilter(MultipleCharFilter):
    def filter(self, qs, value):
        if not value:
            # Even though not a noop, no point filtering if empty.
            return qs

        if self.is_noop(qs, value):
            return qs

        if all(v == '' for v in value):
            return qs

        q = Q()
        for val in value:
            lookups = purl_to_lookups(val)
            if not lookups:
                continue
            q.add(Q(**lookups), Q.OR)

        if q:
            qs = self.get_method(qs)(q)
        else:
            qs = qs.none()

        return qs.distinct() if self.distinct else qs


class PackageFilterSet(FilterSet):
    type = django_filters.CharFilter(
        lookup_expr='iexact',
        help_text='Exact type. (case-insensitive)',
    )
    namespace = django_filters.CharFilter(
        lookup_expr='iexact',
        help_text='Exact namespace. (case-insensitive)',
    )
    name = MultipleCharFilter(
        lookup_expr='iexact',
        help_text='Exact name. Multi-value supported. (case-insensitive)',
    )
    version = MultipleCharFilter(
        help_text='Exact version. Multi-value supported.',
    )
    md5 = MultipleCharInFilter(
        help_text='Exact MD5. Multi-value supported.',
    )
    sha1 = MultipleCharInFilter(
        help_text='Exact SHA1. Multi-value supported.',
    )
    purl = MultiplePackageURLFilter(
        label='Package URL',
    )
    search = PackageSearchFilter(
        label='Search',
        field_name='name',
        lookup_expr='icontains',
    )

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
            'search',
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


class PackagePublicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.prefetch_related('dependencies', 'parties')
    serializer_class = PackageAPISerializer
    lookup_field = 'uuid'
    filterset_class = PackageFilterSet
    throttle_classes = [StaffUserRateThrottle, AnonRateThrottle]

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
        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def get_enhanced_package_data(self, request, *args, **kwargs):
        """
        Return a mapping of enhanced Package data for a given Package
        """
        package = self.get_object()
        package_data = get_enhanced_package(package)
        return Response(package_data)

    @action(detail=False, methods=['post'])
    def filter_by_checksums(self, request, *args, **kwargs):
        """
        Take a mapping, where the keys are the names of the checksum algorthm
        and the values is a list of checksum values and query those values
        against the packagedb.

        Supported checksum fields are:

        - md5
        - sha1
        - sha256
        - sha512

        Example:

            {
                "sha1": [
                    "b55fd82f80cc1bd0bdabf9c6e3153788d35d7911",
                    "27afff2610b5a94274a2311f8b15e514446b0e76
                ]
            }

        Multiple checksums algorithms can be passed together:

            {
                "sha1": [
                    "b55fd82f80cc1bd0bdabf9c6e3153788d35d7911",
                    "27afff2610b5a94274a2311f8b15e514446b0e76
                ],
                "md5": [
                    "e927df60b093456d4e611ae235c1aa5b"
                ]
            }

        This will return Packages whose sha1 or md5 matches those values.
        """
        data = dict(request.data)

        unsupported_fields = []
        supported_fields = ['md5', 'sha1', 'sha256', 'sha512', 'enhance_package_data']
        for field, value in data.items():
            if field not in supported_fields:
                unsupported_fields.append(field)

        if unsupported_fields:
            unsupported_fields_str = ', '.join(unsupported_fields)
            response_data = {
                'status': f'Unsupported field(s) given: {unsupported_fields_str}'
            }
            return Response(response_data)

        enhance_package_data = data.pop('enhance_package_data', False)
        if not data:
            response_data = {
                'status': 'No values provided'
            }
            return Response(response_data)

        lookups = Q()
        for field, value in data.items():
            # Subquery to get the ids of the Packages with the earliest release_date for each `field`
            earliest_release_dates = Package.objects.filter(
                **{field: OuterRef(field)}
            ).order_by('release_date').values('id')[:1]

            value = value or []
            lookups |= Q(
                **{
                    f'{field}__in': value,
                    'id__in': Subquery(earliest_release_dates),
                }
            )

        # Query to get the full Package objects with the earliest release_date for each sha1
        qs = Package.objects.filter(lookups)
        paginated_qs = self.paginate_queryset(qs)
        if enhance_package_data:
            serialized_package_data = [get_enhanced_package(package=package) for package in paginated_qs]
        else:
            serializer = PackageAPISerializer(paginated_qs, many=True, context={'request': request})
            serialized_package_data = serializer.data
        return self.get_paginated_response(serialized_package_data)


class PackageViewSet(PackagePublicViewSet):
    @action(detail=True)
    def reindex_package(self, request, *args, **kwargs):
        """
        Reindex this package instance
        """
        package = self.get_object()
        package.reindex()
        data = {
            'status': f'{package.package_url} has been queued for reindexing'
        }
        return Response(data)


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
    'last_modified_date',
]


def get_enhanced_package(package):
    """
    Return package data from `package`, where the data has been enhanced by
    other packages in the same package_set.
    """
    package_content = package.package_content
    in_package_sets = package.package_sets.count() > 0
    if (
        not in_package_sets
        or not package_content
        or package_content == PackageContentType.SOURCE_REPO
    ):
        # Return unenhanced package data for packages that are not in a package
        # set or are source repo packages.
        # Source repo packages can't really be enhanced much further, datawise
        # and we can't enhance a package that is not in a package set.
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
    package_data = package.to_dict()
    for peer in packages:
        if peer.package_content >= package.package_content:
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


class PackageWatchViewSet(CreateListRetrieveUpdateViewSetMixin):
    """
    Take a `purl` and periodically watch for the new version of the package.
    Add the new package version to the scan queue.
    Default watch interval is 7 days.
    """
    queryset = PackageWatch.objects.get_queryset().order_by('-id')
    serializer_class = PackageWatchAPISerializer
    lookup_field = 'package_url'
    lookup_value_regex = r'pkg:[a-zA-Z0-9_]+\/[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]+)*'
    http_method_names = ['get', 'post', 'patch']

    def get_serializer_class(self):
        if self.action == 'create':
            return PackageWatchCreateSerializer
        elif self.request.method == 'PATCH':
            return PackageWatchUpdateSerializer
        return super().get_serializer_class()


class CollectViewSet(viewsets.ViewSet):
    """
    Return Package data for the purl passed in the `purl` query parameter.

    If the package does not exist, we will fetch the Package data and return
    it in the same request.

    **Note:** Use `Index packages` for bulk indexing/reindexing of packages.
    """
    serializer_class=None
    @extend_schema(
            parameters=[
                OpenApiParameter('purl', str, 'query', description='PackageURL'),
                OpenApiParameter('source_purl', str, 'query', description='Source PackageURL', default=False),
            ],
            responses={200:PackageAPISerializer()},
    )
    def list(self, request, format=None):
        purl = request.query_params.get('purl')
        source_purl = request.query_params.get('source_purl', None)

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
            if source_purl:
                source_package_url = PackageURL.from_string(source_purl)
        except ValueError as e:
            message = {
                'status': f'purl validation error: {e}'
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        lookups = purl_to_lookups(purl)
        packages = Package.objects.filter(**lookups)
        if packages.count() == 0:
            try:
                kwargs = dict()
                if source_purl:
                    kwargs["source_purl"] = source_purl
                errors = priority_router.process(purl, **kwargs)
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
                        'status': f'error(s) occurred when fetching metadata for {purl}: {errors}'
                    }
                return Response(message)

        serializer = PackageAPISerializer(packages, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        request=IndexPackagesSerializer,
        responses={
            200: IndexPackagesResponseSerializer(),
        },
    )
    @action(detail=False, methods=['post'], serializer_class=IndexPackagesSerializer)
    def index_packages(self, request, *args, **kwargs):
        """
        Take a list of `packages` (where each item is a dictionary containing either PURL
        or versionless PURL along with vers range, optionally with source package PURL)
        and index it.

        If `reindex` flag is True then existing package will be rescanned, if `reindex_set`
        is True then all the package in the same set will be rescanned.
        If reindex flag is set to true then all the non existing package will be indexed.

        **Note:** When a versionless PURL is supplied without a vers range, then all the versions
        of that package will be considered for indexing/reindexing.

        **Request example:**

                {
                    "packages": [
                        {
                            "purl": "pkg:npm/less@1.0.32",
                            "vers": null,
                            "source_purl": None
                        },
                        {
                            "purl": "pkg:npm/less",
                            "vers": "vers:npm/>=1.1.0|<=1.1.4",
                            "source_purl": None
                        },
                        {
                            "purl": "pkg:npm/foobar",
                            "vers": null,
                            "source_purl": None
                        }
                    ]
                    "reindex": true,
                    "reindex_set": false,
                }

        Then return a mapping containing:

        - queued_packages_count
            - The number of package urls placed on the index queue.
        - queued_packages
            - A list of package urls that were placed on the index queue.
        - requeued_packages_count
            - The number of existing package urls placed on the rescan queue.
        - requeued_packages
            - A list of existing package urls that were placed on the rescan queue.
        - unqueued_packages_count
            - The number of package urls not placed on the index queue.
                This is because the package url already exists on the index queue and has not
                yet been processed.
        - unqueued_packages
            - A list of package urls that were not placed on the index queue.
        - unsupported_packages_count
            - The number of package urls that are not processable by the index queue.
        - unsupported_packages
            - A list of package urls that are not processable by the index queue.
                The package indexing queue can only handle npm and maven purls.
        - unsupported_vers_count
            - The number of vers range that are not supported by the univers or package_manager.
        - unsupported_vers
            - A list of vers range that are not supported by the univers or package_manager.
        """
        def _reindex_package(package, reindexed_packages):
            if package in reindexed_packages:
                return
            package.reindex()
            reindexed_packages.append(package)

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)

        validated_data = serializer.validated_data
        packages = validated_data.get('packages', [])
        reindex = validated_data.get('reindex', False)
        reindex_set = validated_data.get('reindex_set', False)

        queued_packages = []
        unqueued_packages = []

        nonexistent_packages = []
        reindexed_packages = []
        requeued_packages = []

        supported_ecosystems = ['maven', 'npm', 'deb', 'generic', 'gnu', 'openssl', 'github', 'conan']

        unique_packages, unsupported_packages, unsupported_vers = get_resolved_packages(packages, supported_ecosystems)

        if reindex:
            for package in unique_packages:
                purl = package['purl']
                lookups = purl_to_lookups(purl)
                packages = Package.objects.filter(**lookups)
                if packages.count() > 0:
                    for package in packages:
                        _reindex_package(package, reindexed_packages)
                        if reindex_set:
                            for package_set in package.package_sets.all():
                                for p in package_set.packages.all():
                                    _reindex_package(p, reindexed_packages)
                else:
                    nonexistent_packages.append(package)
            requeued_packages.extend([p.package_url for p in reindexed_packages])

        if not reindex or nonexistent_packages:
            interesting_packages = nonexistent_packages if nonexistent_packages else unique_packages
            for package in interesting_packages:
                purl = package['purl']
                is_routable_purl = priority_router.is_routable(purl)
                if not is_routable_purl:
                    unsupported_packages.append(purl)
                else:
                    # add to queue
                    extra_fields = dict()
                    if source_purl := package.get('source_purl'):
                        extra_fields["source_uri"] = source_purl
                    priority_resource_uri = PriorityResourceURI.objects.insert(purl, **extra_fields)
                    if priority_resource_uri:
                        queued_packages.append(purl)
                    else:
                        unqueued_packages.append(purl)

        response_data = {
            'queued_packages_count': len(queued_packages),
            'queued_packages': queued_packages,
            'requeued_packages_count': len(requeued_packages),
            'requeued_packages': requeued_packages,
            'unqueued_packages_count': len(unqueued_packages),
            'unqueued_packages': unqueued_packages,
            'unsupported_packages_count': len(unsupported_packages),
            'unsupported_packages': unsupported_packages,
            'unsupported_vers_count': len(unsupported_vers),
            'unsupported_vers': unsupported_vers,
        }

        serializer = IndexPackagesResponseSerializer(response_data, context={'request': request})
        return Response(serializer.data)


class PurlValidateViewSet(viewsets.ViewSet):
    """
    Take a `purl` and check whether it's valid PackageURL or not.
    Optionally set `check_existence` to true to check whether the package exists in real world.

    **Note:** As of now `check_existence` only supports `cargo`, `composer`, `deb`,
    `gem`, `golang`, `hex`, `maven`, `npm`, `nuget` and `pypi` ecosystems.

    **Example request:**
            ```
            GET /api/validate/?purl=pkg:npm/foobar@12.3.1&check_existence=false
            ```

    Response contains:

    - valid
        - True, if input PURL is a valid PackageURL.
    - exists
        - True, if input PURL exists in real world and `check_existence` flag is enabled.
    """
    serializer_class = PurlValidateSerializer

    def get_view_name(self):
        return 'Validate PURL'

    @extend_schema(
        parameters=[
            OpenApiParameter('purl', str, 'query', description='PackageURL'),
            OpenApiParameter('check_existence', bool, 'query', description='Check existence', default=False),
        ],
        responses={200: PurlValidateResponseSerializer()},
    )
    def list(self, request):
        serializer = self.serializer_class(data=request.query_params)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        purl = validated_data.get('purl')
        check_existence = validated_data.get('check_existence', False)

        message_valid = "The provided PackageURL is valid."
        message_not_valid = "The provided PackageURL is not valid."
        message_valid_and_exists = (
            "The provided Package URL is valid, and the package exists in the upstream repo."
        )
        message_valid_but_does_not_exist = (
            "The provided PackageURL is valid, but does not exist in the upstream repo."
        )
        message_valid_but_package_type_not_supported = (
            "The provided PackageURL is valid, but `check_existence` is not supported for this package type."
        )

        response = {}
        response['exists'] = None
        response['purl'] = purl
        response['valid'] = False
        response['message'] = message_not_valid

        # validate purl
        try:
            package_url = PackageURL.from_string(purl)
        except ValueError:
            serializer = PurlValidateResponseSerializer(response, context={'request': request})
            return Response(serializer.data)


        response['valid'] = True
        response["message"] = message_valid
        unsupported_ecosystem = False
        if check_existence:
            response['exists'] = False
            lookups = purl_to_lookups(purl)
            packages = Package.objects.filter(**lookups)
            if packages.exists():
                response['exists'] = True
            else:
                versionless_purl = PackageURL(
                    type=package_url.type,
                    namespace=package_url.namespace,
                    name=package_url.name,
                )
                if (
                    package_url.type in VERSION_API_CLASSES_BY_PACKAGE_TYPE
                    and package_url.type in VERSION_CLASS_BY_PACKAGE_TYPE
                ):
                    all_versions = get_all_versions_plain(versionless_purl)
                    if all_versions and (not package_url.version or (
                        package_url.version in all_versions)
                    ):
                        # True, if requested purl has no version and any version of package exists upstream.
                        # True, if requested purl.version exists upstream.
                        response['exists'] = True
                else:
                    unsupported_ecosystem = True

            if response['exists']:
                response["message"] = message_valid_and_exists
            elif unsupported_ecosystem:
                response['exists'] = None
                response["message"] = message_valid_but_package_type_not_supported
            else:
                response["message"] =message_valid_but_does_not_exist

        serializer = PurlValidateResponseSerializer(response, context={'request': request})
        return Response(serializer.data)


def get_resolved_packages(packages, supported_ecosystems):
    """
    Take a list of dict containing purl or version-less purl along with vers
    and return a list of package dicts containing resolved purls, a list of
    unsupported purls, and a list of unsupported vers.
    """
    resolved_packages_by_purl = {}
    unsupported_purls = set()
    unsupported_vers = set()

    for package in packages or []:
        purl = package.get('purl')
        vers = package.get('vers')

        if not purl:
            continue

        try:
            parsed_purl = PackageURL.from_string(purl)
        except ValueError:
            unsupported_purls.add(purl)
            continue

        if parsed_purl.type not in supported_ecosystems:
            unsupported_purls.add(purl)
            continue

        if parsed_purl.version:
            resolved_packages_by_purl[purl] = package
            continue

        # Versionless PURL without any vers-range should give all versions.
        if not vers and not parsed_purl.version:
            if resolved_purls := resolve_all_versions(parsed_purl):
                for res_purl in resolved_purls:
                    resolved_packages_by_purl[res_purl] = {'purl': res_purl}
            continue

        if resolved_purls := resolve_versions(parsed_purl, vers):
            for res_purl in resolved_purls:
                resolved_packages_by_purl[res_purl] = {'purl': res_purl}
        else:
            unsupported_vers.add(vers)
    
    unique_resolved_packages = resolved_packages_by_purl.values()

    return list(unique_resolved_packages), list(unsupported_purls), list(unsupported_vers)


def resolve_all_versions(parsed_purl):
    """
    Take versionless and return a list of PURLs for all the released versions.
    """
    all_versions = get_all_versions(parsed_purl) or []

    return [
        str(
            PackageURL(
                type=parsed_purl.type,
                namespace=parsed_purl.namespace,
                name=parsed_purl.name,
                version=version.string,
            )
        )
        for version in all_versions
    ]


def resolve_versions(parsed_purl, vers):
    """
    Take version-less purl along with vers range and return
    list of all the purls satisfying the vers range.
    """
    if not parsed_purl or not vers:
        return

    try:
        version_range = VersionRange.from_string(vers)
    except ValueError:
        return

    if not version_range.constraints:
        return

    all_versions = get_all_versions(parsed_purl) or []

    result = []
    for version in all_versions:
        try:
            if version in version_range:
                package_url = PackageURL(
                    type=parsed_purl.type,
                    namespace=parsed_purl.namespace,
                    name=parsed_purl.name,
                    version=version.string,
                )
                result.append(str(package_url))
        except InvalidConstraintsError:
            logger.warning(f"Invalid constraints sequence in '{vers}' for '{parsed_purl}'")
            return

    return result


def get_all_versions_plain(purl: PackageURL):
    """
    Return all the versions available for the given purls.
    """
    if (
        purl.type not in VERSION_API_CLASSES_BY_PACKAGE_TYPE
        or purl.type not in VERSION_CLASS_BY_PACKAGE_TYPE
    ):
        return

    package_name = get_api_package_name(purl)
    versionAPI = get_version_fetcher(purl)

    if not package_name or not versionAPI:
        return

    all_versions = versionAPI().fetch(package_name) or []
    return [ version.value for version in all_versions ]


def get_all_versions(purl):
    """
    Return all the versions available for the given purls as
    proper Version objects from `univers`.
    """
    all_versions = get_all_versions_plain(purl)
    versionClass = VERSION_CLASS_BY_PACKAGE_TYPE.get(purl.type)

    result = []
    for version in all_versions:
        try:
            result.append(versionClass(version))
        except InvalidVersion:
            logger.warning(f"Invalid version '{version}' for '{purl}'")
            pass

    return result


VERSION_CLASS_BY_PACKAGE_TYPE = {pkg_type: range_class.version_class for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()}
