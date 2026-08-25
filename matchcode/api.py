#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from uuid import uuid4

from django.db.models import Q
from django.forms import widgets
from django.forms.fields import MultipleChoiceField

from django_filters.filters import MultipleChoiceFilter
from django_filters.rest_framework import FilterSet
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ExactFileIndex
from matchcode.models import ExactPackageArchiveIndex
from matchcode_toolkit.fingerprinting import create_halohash_chunks
from matchcode_toolkit.fingerprinting import hexstring_to_binarray
from matchcode_toolkit.fingerprinting import split_fingerprint
from rest_framework import mixins
from rest_framework import renderers
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import CharField
from rest_framework.serializers import FloatField
from rest_framework.serializers import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ReadOnlyField
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ReadOnlyModelViewSet
from samecode.halohash import byte_hamming_distance
from scanpipe.api import ExcludeFromListViewMixin
from scanpipe.api.serializers import InputSourceSerializer
from scanpipe.api.serializers import SerializerExcludeFieldsMixin
from scanpipe.api.serializers import StrListField
from scanpipe.api.views import ProjectFilterSet
from scanpipe.api.views import RunViewSet
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.pipes import count_group_by
from scanpipe.pipes.fetch import check_urls_availability
from scanpipe.pipes.fetch import fetch_urls
from scanpipe.views import project_results_json_response


class BaseFileIndexSerializer(ModelSerializer):
    sha1 = CharField(source="fingerprint")
    package = HyperlinkedRelatedField(
        view_name="api:package-detail", lookup_field="uuid", read_only=True
    )


class ExactFileIndexSerializer(BaseFileIndexSerializer):
    class Meta:
        model = ExactFileIndex
        fields = ("sha1", "package")


class ExactPackageArchiveIndexSerializer(BaseFileIndexSerializer):
    class Meta:
        model = ExactPackageArchiveIndex
        fields = ("sha1", "package")


class BaseDirectoryIndexSerializer(ModelSerializer):
    fingerprint = ReadOnlyField()
    package = HyperlinkedRelatedField(
        view_name="api:package-detail", lookup_field="uuid", read_only=True
    )


class ApproximateDirectoryContentIndexSerializer(BaseDirectoryIndexSerializer):
    class Meta:
        model = ApproximateDirectoryContentIndex
        fields = (
            "fingerprint",
            "package",
        )


class ApproximateDirectoryStructureIndexSerializer(BaseDirectoryIndexSerializer):
    class Meta:
        model = ApproximateDirectoryStructureIndex
        fields = (
            "fingerprint",
            "package",
        )


class BaseDirectoryIndexMatchSerializer(Serializer):
    fingerprint = CharField()
    matched_fingerprint = CharField()
    package = HyperlinkedRelatedField(
        view_name="api:package-detail", lookup_field="uuid", read_only=True
    )
    similarity_score = FloatField()


class CharMultipleWidget(widgets.TextInput):
    """
    Enables the support for `MultiValueDict` `?field=a&field=b`
    reusing the `SelectMultiple.value_from_datadict()` but render as a `TextInput`.
    """

    def value_from_datadict(self, data, files, name):
        value = widgets.SelectMultiple().value_from_datadict(data, files, name)
        if not value or value == [""]:
            return ""

        return value

    def format_value(self, value):
        """Return a value as it should appear when rendered in a template."""
        return ", ".join(value)


class MultipleCharField(MultipleChoiceField):
    """Overrides `MultipleChoiceField` to fit in `MultipleCharFilter`."""

    widget = CharMultipleWidget

    def valid_value(self, value):
        return True


class MultipleCharFilter(MultipleChoiceFilter):
    """Filters on multiple values for a CharField type using `?field=a&field=b` URL syntax."""

    field_class = MultipleCharField


# TODO: Think of a better name for this filter
class MultipleCharInFilter(MultipleCharFilter):
    def filter(self, qs, value):
        if not value:
            # Even though not a noop, no point filtering if empty.
            return qs

        if self.is_noop(qs, value):
            return qs

        predicate = self.get_filter_predicate(value)
        old_field_name = next(iter(predicate))
        new_field_name = f"{old_field_name}__in"
        predicate[new_field_name] = predicate[old_field_name]
        predicate.pop(old_field_name)

        q = Q(**predicate)
        qs = self.get_method(qs)(q)

        return qs.distinct() if self.distinct else qs


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
                    chunk4=chunk4,
                ),
                Q.OR,
            )

        return qs.filter(q)


class BaseFileIndexFilterSet(FilterSet):
    sha1 = MultipleSHA1Filter()


class ExactFileIndexFilterSet(BaseFileIndexFilterSet):
    class Meta:
        model = ExactFileIndex
        fields = ("sha1",)


class ExactPackageArchiveFilterSet(BaseFileIndexFilterSet):
    class Meta:
        model = ExactPackageArchiveIndex
        fields = ("sha1",)


class BaseDirectoryIndexFilterSet(FilterSet):
    fingerprint = MultipleFingerprintFilter()


class ApproximateDirectoryContentFilterSet(BaseDirectoryIndexFilterSet):
    class Meta:
        model = ApproximateDirectoryContentIndex
        fields = ("fingerprint",)


class ApproximateDirectoryStructureFilterSet(BaseDirectoryIndexFilterSet):
    class Meta:
        model = ApproximateDirectoryStructureIndex
        fields = ("fingerprint",)


class BaseFileIndexViewSet(ReadOnlyModelViewSet):
    lookup_field = "sha1"


class ExactFileIndexViewSet(BaseFileIndexViewSet):
    queryset = ExactFileIndex.objects.all()
    serializer_class = ExactFileIndexSerializer
    filterset_class = ExactFileIndexFilterSet


class ExactPackageArchiveIndexViewSet(BaseFileIndexViewSet):
    queryset = ExactPackageArchiveIndex.objects.all()
    serializer_class = ExactPackageArchiveIndexSerializer
    filterset_class = ExactPackageArchiveFilterSet


class BaseDirectoryIndexViewSet(ReadOnlyModelViewSet):
    lookup_field = "fingerprint"

    @action(detail=False)
    def match(self, request):
        fingerprints = request.query_params.getlist("fingerprint")
        if not fingerprints:
            return Response()

        ecosystems = request.query_params.getlist("ecosystems")
        exclude_purls = request.query_params.getlist("exclude_purls")
        model_class = self.get_serializer().Meta.model
        results = []
        unique_fingerprints = set(fingerprints)
        for fingerprint in unique_fingerprints:
            matches = model_class.match(
                fingerprint, ecosystems=ecosystems, exclude_purls=exclude_purls
            )
            for match in matches:
                _, bah128 = split_fingerprint(fingerprint)
                # Get fingerprint from the match
                fp = match.fingerprint()
                _, match_bah128 = split_fingerprint(fp)
                hd = byte_hamming_distance(bah128, match_bah128)
                similarity_score = (128 - hd) / 128
                results.append(
                    {
                        "fingerprint": fingerprint,
                        "matched_fingerprint": fp,
                        "package": match.package,
                        "similarity_score": similarity_score,
                    }
                )

        serialized_match_results = BaseDirectoryIndexMatchSerializer(
            results, context={"request": request}, many=True
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


class RunSerializer(SerializerExcludeFieldsMixin, serializers.ModelSerializer):
    project = serializers.HyperlinkedRelatedField(view_name="api:run-detail", read_only=True)

    class Meta:
        model = Run
        fields = [
            "url",
            "pipeline_name",
            "status",
            "description",
            "project",
            "uuid",
            "created_date",
            "scancodeio_version",
            "task_id",
            "task_start_date",
            "task_end_date",
            "task_exitcode",
            "task_output",
            "log",
            "execution_time",
        ]
        extra_kwargs = {
            "url": {
                "view_name": "api:run-detail",
                "lookup_field": "pk",
            },
        }


class RunViewSet(RunViewSet):
    serializer_class = RunSerializer


class MatchingSerializer(ExcludeFromListViewMixin, serializers.ModelSerializer):
    upload_file = serializers.FileField(write_only=True, required=False)
    input_urls = StrListField(
        write_only=True,
        required=False,
        style={"base_template": "textarea.html"},
    )
    webhook_url = serializers.CharField(write_only=True, required=False)
    runs = RunSerializer(many=True, read_only=True)
    input_sources = InputSourceSerializer(
        source="inputsources",
        many=True,
        read_only=True,
    )
    codebase_resources_summary = serializers.SerializerMethodField()
    discovered_packages_summary = serializers.SerializerMethodField()
    discovered_dependencies_summary = serializers.SerializerMethodField()
    codebase_relations_summary = serializers.SerializerMethodField()

    ecosystems = serializers.ChoiceField(
        choices=(
            ("", "---------"),
            ("maven", "maven"),
        ),
        required=False,
        allow_blank=True,
        default="",
        write_only=True,
        help_text="Ecosystem to restrict the match index.",
    )

    exclude_purls = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        write_only=True,
        style={"base_template": "textarea.html"},
        help_text="Exclude PURLs (space or comma separated).",
    )

    ecosystems_filter = serializers.SerializerMethodField(read_only=True)
    exclude_purls_filter = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = (
            "url",
            "uuid",
            "upload_file",
            "input_urls",
            "webhook_url",
            "created_date",
            "input_sources",
            "runs",
            "resource_count",
            "package_count",
            "dependency_count",
            "relation_count",
            "codebase_resources_summary",
            "discovered_packages_summary",
            "discovered_dependencies_summary",
            "codebase_relations_summary",
            "ecosystems",
            "exclude_purls",
            "ecosystems_filter",
            "exclude_purls_filter",
        )
        exclude_from_list_view = [
            "resource_count",
            "package_count",
            "dependency_count",
            "relation_count",
            "codebase_resources_summary",
            "discovered_packages_summary",
            "discovered_dependencies_summary",
            "codebase_relations_summary",
        ]
        extra_kwargs = {
            "url": {
                "view_name": "api:matching-detail",
                "lookup_field": "pk",
            },
        }

    def get_codebase_resources_summary(self, project):
        queryset = project.codebaseresources.all()
        return count_group_by(queryset, "status")

    def get_discovered_packages_summary(self, project):
        base_qs = project.discoveredpackages
        return {
            "total": base_qs.count(),
            "with_missing_resources": base_qs.exclude(missing_resources=[]).count(),
            "with_modified_resources": base_qs.exclude(modified_resources=[]).count(),
        }

    def get_discovered_dependencies_summary(self, project):
        base_qs = project.discovereddependencies
        return {
            "total": base_qs.count(),
            "is_runtime": base_qs.filter(is_runtime=True).count(),
            "is_optional": base_qs.filter(is_optional=True).count(),
            "is_pinned": base_qs.filter(is_pinned=True).count(),
        }

    def get_codebase_relations_summary(self, project):
        queryset = project.codebaserelations.all()
        return count_group_by(queryset, "map_type")

    def get_ecosystems_filter(self, project):
        return (project.extra_data or {}).get("ecosystems", [])

    def get_exclude_purls_filter(self, project):
        return (project.extra_data or {}).get("exclude_purls", [])

    def validate_input_urls(self, value):
        """Add support for providing multiple URLs in a single string."""
        return [url for entry in value for url in entry.split()]

    def create(self, validated_data, matching_pipeline_name="matching"):
        """Create a new `project` with `upload_file`, using the `matching` pipeline"""
        execute_now = True
        validated_data["name"] = uuid4()
        upload_file = validated_data.pop("upload_file", None)
        input_urls = validated_data.pop("input_urls", [])
        webhook_url = validated_data.pop("webhook_url", None)
        ecosystems = validated_data.pop("ecosystems", "")
        exclude_purls = validated_data.pop("exclude_purls", "")

        # Convert ecosystems to a list
        if isinstance(ecosystems, str):
            ecosystems = [ecosystems] if ecosystems else []

        # Convert exclude_purls to a list; support spaces, commas, and newlines
        if isinstance(exclude_purls, str):
            exclude_purls = [
                purl.strip() for purl in exclude_purls.replace(",", " ").split() if purl.strip()
            ]

        downloads, errors = fetch_urls(input_urls)
        if errors:
            raise serializers.ValidationError("Could not fetch: " + "\n".join(errors))

        project = super().create(validated_data)

        project.extra_data = project.extra_data or {}
        if ecosystems:
            project.extra_data["ecosystems"] = ecosystems

        if exclude_purls:
            project.extra_data["exclude_purls"] = exclude_purls

        if ecosystems or exclude_purls:
            project.save()

        if upload_file:
            project.add_uploads([upload_file])

        if downloads:
            project.add_downloads(downloads)

        if webhook_url:
            project.add_webhook_subscription(webhook_url)

        project.add_pipeline(matching_pipeline_name, execute_now)

        return project


class D2DSerializer(ExcludeFromListViewMixin, serializers.ModelSerializer):
    input_urls = StrListField(
        write_only=True,
        required=True,
        style={"base_template": "textarea.html"},
    )

    codebase_resources_summary = serializers.SerializerMethodField()
    discovered_packages_summary = serializers.SerializerMethodField()
    discovered_dependencies_summary = serializers.SerializerMethodField()
    codebase_relations_summary = serializers.SerializerMethodField()
    codebase_resources_discrepancies = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "url",
            "uuid",
            "input_urls",
            "created_date",
            "input_sources",
            "runs",
            "resource_count",
            "package_count",
            "dependency_count",
            "relation_count",
            "codebase_resources_summary",
            "discovered_packages_summary",
            "discovered_dependencies_summary",
            "codebase_relations_summary",
            "codebase_resources_discrepancies",
        )
        exclude_from_list_view = [
            "resource_count",
            "package_count",
            "dependency_count",
            "relation_count",
            "codebase_resources_summary",
            "discovered_packages_summary",
            "discovered_dependencies_summary",
            "codebase_relations_summary",
            "codebase_resources_discrepancies",
        ]
        extra_kwargs = {
            "url": {
                "view_name": "api:d2d-detail",
                "lookup_field": "pk",
            },
        }

    def get_codebase_resources_summary(self, project):
        queryset = project.codebaseresources.all()
        return count_group_by(queryset, "status")

    def get_codebase_resources_discrepancies(self, project):
        queryset = project.codebaseresources.filter(status="requires-review")
        return {
            "total": queryset.count(),
        }

    def get_discovered_packages_summary(self, project):
        base_qs = project.discoveredpackages
        return {
            "total": base_qs.count(),
            "with_missing_resources": base_qs.exclude(missing_resources=[]).count(),
            "with_modified_resources": base_qs.exclude(modified_resources=[]).count(),
        }

    def get_discovered_dependencies_summary(self, project):
        base_qs = project.discovereddependencies
        return {
            "total": base_qs.count(),
            "is_runtime": base_qs.filter(is_runtime=True).count(),
            "is_optional": base_qs.filter(is_optional=True).count(),
            "is_pinned": base_qs.filter(is_pinned=True).count(),
        }

    def get_codebase_relations_summary(self, project):
        queryset = project.codebaserelations.all()
        return count_group_by(queryset, "map_type")

    def create(self, validated_data, matching_pipeline_name="d2d"):
        """Create a new `project` with `input_urls`, using the `d2d` pipeline"""
        execute_now = True
        validated_data["name"] = uuid4()
        input_urls = validated_data.pop("input_urls", [])
        errors = check_urls_availability(input_urls)

        if errors:
            raise serializers.ValidationError("Could not fetch: " + "\n".join(errors))

        project = super().create(validated_data)

        urls = []

        for url in input_urls:
            value = url
            if "\n" in value:
                input_urls = input_urls[0].split("\n")
                input_urls = [x.strip() for x in input_urls]
                input_urls = list(filter(None, input_urls))
                urls.extend(input_urls)
            else:
                value = value.strip()
                if value:
                    urls.append(value)

        for url in urls:
            project.add_input_source(download_url=url)

        project.add_pipeline(
            matching_pipeline_name,
            selected_groups=["Java", "Javascript", "Elf", "Go"],
            execute_now=execute_now,
        )

        return project


class MatchingViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Take a ScanCode.io JSON of a codebase `upload_file` or from a list of
    `input_urls` and run the ``matching`` pipeline
    (https://github.com/aboutcode-org/purldb/blob/main/matchcode/pipelines/matching.py)
    on it.

    The ``matching`` pipeline matches directory and resources of the codebase in
    ``upload_file`` to Packages indexed in the PurlDB.

    **Request example:**

            {
                "input_urls": <file contents in binary buffer>
            }

    Then return a mapping containing information about the match request:

    - url
        - URL of the match request
    - uuid
        - UUID of the match request
    - created_date
        - Date of the match request
    - input_sources
        - List of input files for the match request
    - runs
        - List of mapping containing details about the runs created for this
          match request.
    """

    queryset = Project.objects.all()
    serializer_class = MatchingSerializer
    filterset_class = ProjectFilterSet

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "runs",
            )
        )

    @action(detail=True, renderer_classes=[renderers.JSONRenderer])
    def results(self, request, *args, **kwargs):
        """
        Return the results compatible with ScanCode data format.
        The content is returned as a stream of JSON content using the
        JSONResultsGenerator class.
        """
        return project_results_json_response(self.get_object())


class D2DViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Take a list of `input_urls` containing package download urls and match it to its source.

    **Request example:**

            {
                "input_urls": [
                    "https://registry.npmjs.com/asdf/-/asdf-1.0.2.tgz"
                ]
            }

    Then return a mapping containing information about the match request:

    - url
        - URL of the match request
    - uuid
        - UUID of the match request
    - created_date
        - Date of the match request
    - input_sources
        - List of input files for the match request
    - runs
        - List of mapping containing details about the runs created for this
          match request.
    """

    queryset = Project.objects.all()
    serializer_class = D2DSerializer
    filterset_class = ProjectFilterSet

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "runs",
            )
        )

    @action(detail=True, renderer_classes=[renderers.JSONRenderer])
    def results(self, request, *args, **kwargs):
        """
        Return the results compatible with ScanCode data format.
        The content is returned as a stream of JSON content using the
        JSONResultsGenerator class.
        """
        return project_results_json_response(self.get_object())
