#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.db.models import Q
from django.forms import widgets
from django.forms.fields import MultipleChoiceField
from django_filters.filters import MultipleChoiceFilter
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import CharField
from rest_framework.serializers import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ReadOnlyField
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ReadOnlyModelViewSet

from matchcode.fingerprinting import create_halohash_chunks
from matchcode.fingerprinting import split_fingerprint
from matchcode.models import ExactFileIndex
from matchcode.models import ExactPackageArchiveIndex
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.utils import hexstring_to_binarray


class BaseFileIndexSerializer(ModelSerializer):
    sha1 = CharField(source='fingerprint')
    package = HyperlinkedRelatedField(view_name='api:package-detail', lookup_field='uuid', read_only=True)


class ExactFileIndexSerializer(BaseFileIndexSerializer):
    class Meta:
        model = ExactFileIndex
        fields = (
            'sha1',
            'package'
        )


class ExactPackageArchiveIndexSerializer(BaseFileIndexSerializer):
    class Meta:
        model = ExactPackageArchiveIndex
        fields = (
            'sha1',
            'package'
        )


class BaseDirectoryIndexSerializer(ModelSerializer):
    fingerprint = ReadOnlyField()
    package = HyperlinkedRelatedField(view_name='api:package-detail', lookup_field='uuid', read_only=True)


class ApproximateDirectoryContentIndexSerializer(BaseDirectoryIndexSerializer):
    class Meta:
        model = ApproximateDirectoryContentIndex
        fields = (
            'fingerprint',
            'package',
        )


class ApproximateDirectoryStructureIndexSerializer(BaseDirectoryIndexSerializer):
    class Meta:
        model = ApproximateDirectoryStructureIndex
        fields = (
            'fingerprint',
            'package',
        )


class BaseDirectoryIndexMatchSerializer(Serializer):
    fingerprint = CharField()
    matched_fingerprint = CharField()
    package = HyperlinkedRelatedField(view_name='api:package-detail', lookup_field='uuid', read_only=True)


class CharMultipleWidget(widgets.TextInput):
    """
    Enables the support for `MultiValueDict` `?field=a&field=b`
    reusing the `SelectMultiple.value_from_datadict()` but render as a `TextInput`.
    """
    def value_from_datadict(self, data, files, name):
        value = widgets.SelectMultiple().value_from_datadict(data, files, name)
        if not value or value == ['']:
            return ''

        return value

    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        return ', '.join(value)


class MultipleCharField(MultipleChoiceField):
    """
    Overrides `MultipleChoiceField` to fit in `MultipleCharFilter`.
    """
    widget = CharMultipleWidget

    def valid_value(self, value):
        return True


class MultipleCharFilter(MultipleChoiceFilter):
    """
    Filters on multiple values for a CharField type using `?field=a&field=b` URL syntax.
    """
    field_class = MultipleCharField


class MultipleSHA1Filter(MultipleCharFilter):
    """
    Overrides `MultipleCharFilter.filter()` to convert the SHA1
    into a bytearray so it can be queried
    """
    def filter(self, qs, value):
        if not value:
            return qs

        q = Q()
        for val in value:
            v = hexstring_to_binarray(val)
            q.add(Q(sha1=v), Q.OR)

        return qs.filter(q)


class MultipleFingerprintFilter(MultipleCharFilter):
    """
    Overrides `MultipleCharFilter.filter()` to process fingerprint from a single
    string into multiple values used for querying.

    In the BaseDirectoryIndex model, the fingerprint is stored in four chunks of
    equal size, not as a single field that contains the entire fingerprint. We
    must process the fingerprint into the correct parts so we can use those
    parts to query the different fields.
    """
    def filter(self, qs, value):
        if not value:
            return qs

        q = Q()
        for val in value:
            indexed_elements_count, bah128 = split_fingerprint(val)
            chunk1, chunk2, chunk3, chunk4 = create_halohash_chunks(bah128)
            q.add(
                Q(
                    indexed_elements_count=indexed_elements_count,
                    chunk1=chunk1,
                    chunk2=chunk2,
                    chunk3=chunk3,
                    chunk4=chunk4
                ),
                Q.OR
            )

        return qs.filter(q)


class BaseFileIndexFilterSet(FilterSet):
    sha1 = MultipleSHA1Filter()


class ExactFileIndexFilterSet(BaseFileIndexFilterSet):
    class Meta:
        model = ExactFileIndex
        fields = (
            'sha1',
        )


class ExactPackageArchiveFilterSet(BaseFileIndexFilterSet):
    class Meta:
        model = ExactPackageArchiveIndex
        fields = (
            'sha1',
        )


class BaseDirectoryIndexFilterSet(FilterSet):
    fingerprint = MultipleFingerprintFilter()


class ApproximateDirectoryContentFilterSet(BaseDirectoryIndexFilterSet):
    class Meta:
        model = ApproximateDirectoryContentIndex
        fields = (
            'fingerprint',
        )


class ApproximateDirectoryStructureFilterSet(BaseDirectoryIndexFilterSet):
    class Meta:
        model = ApproximateDirectoryStructureIndex
        fields = (
            'fingerprint',
        )


class BaseFileIndexViewSet(ReadOnlyModelViewSet):
    lookup_field = 'sha1'


class ExactFileIndexViewSet(BaseFileIndexViewSet):
    queryset = ExactFileIndex.objects.all()
    serializer_class = ExactFileIndexSerializer
    filterset_class = ExactFileIndexFilterSet


class ExactPackageArchiveIndexViewSet(BaseFileIndexViewSet):
    queryset = ExactPackageArchiveIndex.objects.all()
    serializer_class = ExactPackageArchiveIndexSerializer
    filterset_class = ExactPackageArchiveFilterSet


class BaseDirectoryIndexViewSet(ReadOnlyModelViewSet):
    lookup_field = 'fingerprint'

    @action(detail=False)
    def match(self, request):
        fingerprints = request.query_params.getlist('fingerprint')
        if not fingerprints:
            return Response()

        model_class = self.get_serializer().Meta.model
        results = []
        unique_fingerprints = set(fingerprints)
        for fingerprint in unique_fingerprints:
            matches = model_class.match(fingerprint)
            for match in matches:
                results.append(
                    {
                        'fingerprint': fingerprint,
                        'matched_fingerprint': match.fingerprint(),
                        'package': match.package,
                    }
                )

        serialized_match_results = BaseDirectoryIndexMatchSerializer(
            results,
            context={'request': request},
            many=True
        )
        return Response(serialized_match_results.data)


class ApproximateDirectoryContentIndexViewSet(BaseDirectoryIndexViewSet):
    queryset = ApproximateDirectoryContentIndex.objects.all()
    serializer_class = ApproximateDirectoryContentIndexSerializer
    filterset_class = ApproximateDirectoryContentFilterSet


class ApproximateDirectoryStructureIndexViewSet(BaseDirectoryIndexViewSet):
    queryset = ApproximateDirectoryStructureIndex.objects.all()
    serializer_class = ApproximateDirectoryStructureIndexSerializer
    filterset_class = ApproximateDirectoryStructureFilterSet
