#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from uuid import uuid4

from rest_framework import mixins
from rest_framework import renderers
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action

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


class RunSerializer(SerializerExcludeFieldsMixin, serializers.ModelSerializer):
    project = serializers.HyperlinkedRelatedField(
        view_name="matching-detail", read_only=True
    )

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

    class Meta:
        model = Project
        fields = (
            'url',
            'uuid',
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
            'url': {
                'view_name': 'matching-detail',
                'lookup_field': 'pk',
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
            "is_resolved": base_qs.filter(is_resolved=True).count(),
        }

    def get_codebase_relations_summary(self, project):
        queryset = project.codebaserelations.all()
        return count_group_by(queryset, "map_type")

    def validate_input_urls(self, value):
        """Add support for providing multiple URLs in a single string."""
        return [url for entry in value for url in entry.split()]

    def create(self, validated_data, matching_pipeline_name='matching'):
        """
        Create a new `project` with `upload_file`, using the `matching` pipeline
        """
        execute_now = True
        validated_data['name'] = uuid4()
        upload_file = validated_data.pop("upload_file", None)
        input_urls = validated_data.pop("input_urls", [])
        webhook_url = validated_data.pop("webhook_url", None)

        downloads, errors = fetch_urls(input_urls)
        if errors:
            raise serializers.ValidationError("Could not fetch: " + "\n".join(errors))

        project = super().create(validated_data)

        if upload_file:
            project.add_uploads([upload_file])

        if downloads:
            project.add_downloads(downloads)

        if webhook_url:
            project.add_webhook_subscription(webhook_url)

        project.add_pipeline(matching_pipeline_name, execute_now)

        return project


class D2DSerializer(MatchingSerializer):
    input_urls = StrListField(
        write_only=True,
        required=True,
        style={"base_template": "textarea.html"},
    )

    class Meta:
        model = Project
        fields = (
            'url',
            'uuid',
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
            'url': {
                'view_name': 'd2d-detail',
                'lookup_field': 'pk',
            },
        }

    def create(self, validated_data, matching_pipeline_name='d2d'):
        """
        Create a new `project` with `upload_file`, using the `matching` pipeline
        """
        execute_now = True
        validated_data['name'] = uuid4()
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

        project.add_pipeline(matching_pipeline_name, selected_groups=["Java", "Javascript", "Elf", "Go"], execute_now=execute_now)

        return project


class MatchingViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
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
