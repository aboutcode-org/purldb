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

from packagedcode.models import PackageData
from packageurl import PackageURL
from packageurl.contrib.django.utils import purl_to_lookups
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from matchcode.api import MultipleCharFilter
# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from minecode import visitors  # NOQA
from minecode import priority_router
from minecode.models import PriorityResourceURI
from minecode.route import NoRouteAvailable
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
    md5 = MultipleCharFilter(
        help_text="Exact MD5. Multi-value supported.",
    )
    sha1 = MultipleCharFilter(
        help_text="Exact SHA1. Multi-value supported.",
    )


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
    md5 = MultipleCharFilter(
        help_text="Exact MD5. Multi-value supported.",
    )
    sha1 = MultipleCharFilter(
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


def get_package_data(type, namespace, name, version, field):
    """
    Look up the value of a field of a Package
    """
    package = None
    content_types = [
        Package.PackageContentType.SOURCE,
        Package.PackageContentType.BINARY,
        Package.PackageContentType.DOC,
        Package.PackageContentType.TEST,
    ]
    for content_type in content_types:
        try:
            package = Package.objects.get(
                type=type,
                namespace=namespace,
                name=name,
                version=version,
                package_content=content_type
            )
        except Package.DoesNotExist:
            continue
    if not package:
        return None
    return getattr(package, field, None)


def get_mixed_package(type, namespace, name, version):
    """
    return package data that has results mixed from different sources
    """
    packages = Package.objects.filter(
        type=type,
        namespace=namespace,
        name=name,
        version=version,
    )

    # See if we can get a specific version of the package with no qualifiers or subpath
    # if there are multiple, we just choose the first one
    based_package = packages.filter(
        Q(qualifiers__isnull=True) & Q(subpath__isnull=True) |
        Q(qualifiers='') & Q(subpath='') |
        Q(qualifiers__isnull=True) & Q(subpath='') |
        Q(qualifiers='') & Q(subpath__isnull=True)
    ).first()

    if based_package:
        # Use this package metadata as our base
        package_data = based_package.to_dict()
    else:
        # We have to create the metadata
        package_data = PackageData(
            type=type,
            namespace=namespace,
            name=name,
            version=version,
        ).to_dict()

    update = [
        'primary_language',
        'copyright',
        'declared_license_expression',
        'declared_license_expression_spdx',
        'api_data_url',
        'bug_tracking_url',
        'code_view_url',
        'vcs_url',
        'source_packages',
        'api_data_url',
        'datasource_id',
        'repository_homepage_url',
    ]

    dont_update = [
        'type',
        'namespace',
        'name',
        'version',
        'qualifiers',
        'subpath',
        'purl',
    ]

    clear_out = [
        # These should be cleared out
        'download_url',
        'size',
        'md5',
        'sha1',
        'sha256',
        'sha512',
        'package_uid',
    ]

    what_do = [
        'license_detections',
        'other_license_expression'
        'other_license_expression_spdx',
        'other_license_detections',
        'extracted_license_statement',
        'notice_text',
        'extra_data',
        'dependencies',
        'repository_download_url',
        'file_references',
        'parties',
    ]

    for field, data in package_data.items():
        if (
            field in dont_update
            or field in what_do
        ):
            # Skip these
            continue
        elif field in clear_out:
            package_data[field] = None
        elif field in update:
            if not data:
                # For now, we prioritize source results over others
                better_data = get_package_data(
                    type=type,
                    namespace=namespace,
                    name=name,
                    version=version,
                    field=field
                )
                if not better_data:
                    continue
                package_data[field] = better_data
            else:
                # Enhance field with data
                # TODO: figure out which fields are safe to append to
                pass

    return package_data

    # Start layering on fields
    # TODO: Get package that the purl is exactly for, like if its a source package or test package, and use that package as the base
    # then start filling in the data from other sources, based on precidence, source-binary-doc-test, etc)
    # TODO: filter using package se
    # TODO: how are the package_set id's computed? when is it set, etc.

