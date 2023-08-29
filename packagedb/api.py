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
from minecode.models import ScannableURI
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
from packagedb.package_managers import get_api_package_name
from packagedb.package_managers import get_version_fetcher
from packagedb.package_managers import VERSION_API_CLASSES_BY_PACKAGE_TYPE

from univers import versions
from univers.version_range import RANGE_CLASS_BY_SCHEMES
from univers.version_range import InvalidVersionRange
from univers.version_range import VersionRange


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

        q = Q()
        for field, value in data.items():
            # We create this intermediate dictionary so we can modify the field
            # name to have __in at the end
            d = {f'{field}__in': value}
            q |= Q(**d)

        qs = Resource.objects.filter(q)
        paginated_qs = self.paginate_queryset(qs)
        serializer = ResourceAPISerializer(paginated_qs, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


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
        return self.get_paginated_response(serializer.data)

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

    @action(detail=False, methods=['post'])
    def index_packages(self, request, *args, **kwargs):
        """
        Take a list of dictionary where each dictionary has either resolved PURL i.e. PURL with
        version or version-less PURL along with vers range. Then return a mapping containing

        Input example:
            [
                {
                    "purl": "pkg:npm/foobar@12.3.1",
                },
                {
                    "purl": "pkg:npm/foobar",
                    "vers": "vers:npm/>=1.0.0|<=4.1.0"
                }
                ...
            ]

        - queued_packages_count
            - The number of package urls placed on the queue.
        - queued_packages
            - A list of package urls that were placed on the queue.
        - unqueued_packages_count
            - The number of package urls not placed on the queue. This is
              because the package url already exists on the queue and has not
              yet been processed.
        - unqueued_packages
            - A list of package urls that were not placed on the queue.
        - unsupported_packages_count
            - The number of package urls that are not processable by the queue.
        - unsupported_packages
            - A list of package urls that are not processable by the queue. The
              package indexing queue can only handle npm and maven purls.
        - unqueued_packages
            - A list of package urls that were not placed on the queue.
        - unsupported_vers_count
            - The number of vers range that are not supported by the univers or package_manager.
        - unsupported_vers
            - A list of vers range that are not supported by the univers or package_manager.
        """

        packages = request.data.get('packages') or []
        queued_packages = []
        unqueued_packages = []

        unique_purls, unsupported_packages, unsupported_vers = get_resolved_purls(packages)

        for purl in unique_purls:
            is_routable_purl = priority_router.is_routable(purl)
            if not is_routable_purl:
                unsupported_packages.append(purl)
            else:
                # add to queue
                priority_resource_uri = PriorityResourceURI.objects.insert(purl)
                if priority_resource_uri:
                    queued_packages.append(purl)
                else:
                    unqueued_packages.append(purl)
        response_data = {
            'queued_packages_count': len(queued_packages),
            'queued_packages': queued_packages,
            'unqueued_packages_count': len(unqueued_packages),
            'unqueued_packages': unqueued_packages,
            'unsupported_packages_count': len(unsupported_packages),
            'unsupported_packages': unsupported_packages,
            'unsupported_vers_count': len(unsupported_vers),
            'unsupported_vers': unsupported_vers,
        }
        return Response(response_data)

    @action(detail=True)
    def reindex_package(self, request, *args, **kwargs):
        """
        Reindex this package instance
        """
        package = self.get_object()
        package.rescan()
        data = {
            'status': f'{package.package_url} has been queued for reindexing'
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    def reindex_packages(self, request, *args, **kwargs):
        """
        Take a list of `package_urls` and for each Package URL, reindex the
        corresponding package.
        If the field `reindex_set` is True, then the Packages in the same
        package set as the packages from `package_urls` will be reindexed.

        Then return a mapping containing:
        - requeued_packages_count
            - The number of package urls placed on the queue.
        - requeued_packages
            - A list of package urls that were placed on the queue.
        - nonexistent_packages_count
            - The number of package urls that do not correspond to a package in
              the database.
        - nonexistent_packages
            - A list of package urls that do not correspond to a package in the
              database.
        """
        def _reindex_package(package, reindexed_packages):
            if package in reindexed_packages:
                return
            package.rescan()
            reindexed_packages.append(package)

        purls = request.data.getlist('package_urls')
        reindex_set = request.data.get('reindex_set') or False

        nonexistent_packages = []
        reindexed_packages = []
        for purl in purls:
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
                nonexistent_packages.append(purl)

        requeued_packages = [p.package_url for p in reindexed_packages]
        response_data = {
            'requeued_packages_count': len(requeued_packages),
            'requeued_packages': requeued_packages,
            'nonexistent_packages_count': len(nonexistent_packages),
            'nonexistent_packages': nonexistent_packages,
        }
        return Response(response_data)

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
        for field, value in data.items():
            if field not in ('md5', 'sha1', 'sha256', 'sha512', 'enhance_package_data'):
                unsupported_fields.append(field)

        if unsupported_fields:
            unsupported_fields_str = ', '.join(unsupported_fields)
            response_data = {
                'status': f'Unsupported field(s) given: {unsupported_fields_str}'
            }
            return Response(response_data)

        enhance_package_data = data.pop('enhance_package_data', False)
        q = Q()
        for field, value in data.items():
            # We create this intermediate dictionary so we can modify the field
            # name to have __in at the end
            d = {f'{field}__in': value}
            q |= Q(**d)

        qs = Package.objects.filter(q)
        paginated_qs = self.paginate_queryset(qs)
        if enhance_package_data:
            serialized_package_data = [get_enhanced_package(package=package) for package in paginated_qs]
        else:
            serializer = PackageAPISerializer(paginated_qs, many=True, context={'request': request})
            serialized_package_data = serializer.data
        return self.get_paginated_response(serialized_package_data)


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


def get_resolved_purls(packages):
    """
    Take a list of dict containing purl or version-less purl along with vers
    and return a list of resolved purls, a list of unsupported purls, and a 
    list of unsupported vers.
    """
    unique_resolved_purls = set()
    unsupported_purls = set()
    unsupported_vers = set()

    for items in packages or []:
        purl = items.get('purl')
        vers = items.get('vers')

        if not purl:
            continue

        try:
            parsed_purl = PackageURL.from_string(purl)
        except ValueError:
            unsupported_purls.add(purl)
            continue

        if parsed_purl.version:
            unique_resolved_purls.add(purl)
            continue

        if not vers:
            unsupported_purls.add(purl)
            continue

        if resolved:= resolve_versions(parsed_purl, vers):
            unique_resolved_purls.update(resolved)
        else:
            unsupported_vers.add(vers)

    return list(unique_resolved_purls), list(unsupported_purls), list(unsupported_vers)



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
        if version in version_range
    ]

def get_all_versions(purl: PackageURL):
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

    all_versions = versionAPI().fetch(package_name)
    versionClass = VERSION_CLASS_BY_PACKAGE_TYPE.get(purl.type)

    return [versionClass(package_version.value) for package_version in all_versions]


VERSION_CLASS_BY_PACKAGE_TYPE = {pkg_type: range_class.version_class for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()}
