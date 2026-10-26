#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.urls import reverse_lazy

from drf_spectacular.utils import extend_schema_field
from packageurl import PackageURL
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BooleanField
from rest_framework.serializers import CharField
from rest_framework.serializers import DateTimeField
from rest_framework.serializers import FloatField
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import HyperlinkedRelatedField
from rest_framework.serializers import IntegerField
from rest_framework.serializers import JSONField
from rest_framework.serializers import ListField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Serializer
from rest_framework.serializers import SerializerMethodField

from packagedb.models import DependentPackage
from packagedb.models import Package
from packagedb.models import PackageActivity
from packagedb.models import PackageHealthMetrics
from packagedb.models import PackageSet
from packagedb.models import PackageWatch
from packagedb.models import Party
from packagedb.models import Resource


class ResourceAPISerializer(HyperlinkedModelSerializer):
    package = HyperlinkedRelatedField(
        view_name="api:package-detail", lookup_field="uuid", read_only=True
    )
    purl = CharField(source="package.package_url")

    class Meta:
        model = Resource
        fields = (
            "package",
            "purl",
            "path",
            "type",
            "name",
            "extension",
            "size",
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "git_sha1",
            "mime_type",
            "file_type",
            "programming_language",
            "is_binary",
            "is_text",
            "is_archive",
            "is_media",
            "is_key_file",
            "detected_license_expression",
            "detected_license_expression_spdx",
            "license_detections",
            "license_clues",
            "percentage_of_license_text",
            "copyrights",
            "holders",
            "authors",
            "package_data",
            "emails",
            "urls",
            "extra_data",
        )
        read_only_fields = fields


class ResourceMetadataSerializer(HyperlinkedModelSerializer):
    for_packages = JSONField()

    class Meta:
        model = Resource
        fields = (
            "path",
            "type",
            "name",
            "extension",
            "size",
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "git_sha1",
            "mime_type",
            "file_type",
            "programming_language",
            "is_binary",
            "is_text",
            "is_archive",
            "is_media",
            "is_key_file",
            "detected_license_expression",
            "detected_license_expression_spdx",
            "license_detections",
            "license_clues",
            "percentage_of_license_text",
            "copyrights",
            "holders",
            "authors",
            "package_data",
            "for_packages",
            "emails",
            "urls",
            "extra_data",
        )


class PartySerializer(ModelSerializer):
    class Meta:
        model = Party
        fields = (
            "type",
            "role",
            "name",
            "email",
            "url",
        )


class DependentPackageSerializer(ModelSerializer):
    class Meta:
        model = DependentPackage
        fields = (
            "purl",
            "extracted_requirement",
            "scope",
            "is_runtime",
            "is_optional",
            "is_pinned",
        )


class PackageInPackageSetAPISerializer(ModelSerializer):
    """
    Serialize Package instances within a PackageSet that is within a Package in
    the PackageAPISerializer
    """

    class Meta:
        model = Package
        fields = ("uuid",)

    def to_representation(self, instance):
        reverse_uri = reverse_lazy("api:package-detail", kwargs={"uuid": instance.uuid})
        request = self.context["request"]
        return request.build_absolute_uri(reverse_uri)


class PackageSetAPISerializer(ModelSerializer):
    packages = PackageInPackageSetAPISerializer(many=True)

    class Meta:
        model = PackageSet
        fields = (
            "uuid",
            "packages",
        )


class PackageAPISerializer(HyperlinkedModelSerializer):
    dependencies = DependentPackageSerializer(many=True)
    parties = PartySerializer(many=True)
    resources = HyperlinkedIdentityField(view_name="api:package-resources", lookup_field="uuid")
    history = HyperlinkedIdentityField(view_name="api:package-history", lookup_field="uuid")
    url = HyperlinkedIdentityField(view_name="api:package-detail", lookup_field="uuid")
    package_sets = PackageSetAPISerializer(many=True)
    package_content = SerializerMethodField()
    declared_license_expression_spdx = CharField()
    other_license_expression_spdx = CharField()

    class Meta:
        model = Package
        fields = (
            "url",
            "uuid",
            "filename",
            "package_sets",
            "package_content",
            "purl",
            "type",
            "namespace",
            "name",
            "version",
            "qualifiers",
            "subpath",
            "primary_language",
            "description",
            "release_date",
            "parties",
            "keywords",
            "homepage_url",
            "download_url",
            "bug_tracking_url",
            "code_view_url",
            "vcs_url",
            "repository_homepage_url",
            "repository_download_url",
            "api_data_url",
            "size",
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "copyright",
            "holder",
            "declared_license_expression",
            "declared_license_expression_spdx",
            "license_detections",
            "other_license_expression",
            "other_license_expression_spdx",
            "other_license_detections",
            "extracted_license_statement",
            "notice_text",
            "source_packages",
            "extra_data",
            "package_uid",
            "datasource_id",
            "file_references",
            "dependencies",
            "resources",
            "history",
        )
        read_only_fields = fields

    def get_package_content(self, obj):
        return obj.get_package_content_display()


class PackageInPackageSetMetadataSerializer(ModelSerializer):
    """
    Serialize Package instances within a PackageSet that is within a Package in
    the PackageMetadataSerializer
    """

    class Meta:
        model = Package
        fields = ("uuid",)

    def to_representation(self, instance):
        return instance.package_uid


class PackageSetMetadataSerializer(ModelSerializer):
    packages = PackageInPackageSetMetadataSerializer(many=True)

    class Meta:
        model = PackageSet
        fields = (
            "uuid",
            "packages",
        )


class PackageMetadataSerializer(ModelSerializer):
    """
    Serializes the metadata of a Package from the fields of the Package model
    such that the data returned is in the same form as a ScanCode Package scan.

    This differs from PackageSerializer used for the API by the addition of
    the `package_url` field and the exclusion of the `uuid`, and `filename` fields.
    """

    dependencies = DependentPackageSerializer(many=True)
    parties = PartySerializer(many=True)
    package_sets = PackageSetMetadataSerializer(many=True)
    package_content = SerializerMethodField()
    declared_license_expression_spdx = CharField()
    other_license_expression_spdx = CharField()

    class Meta:
        model = Package
        fields = (
            "type",
            "namespace",
            "name",
            "version",
            "qualifiers",
            "subpath",
            "package_sets",
            "package_content",
            "primary_language",
            "description",
            "release_date",
            "parties",
            "keywords",
            "homepage_url",
            "download_url",
            "size",
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "bug_tracking_url",
            "code_view_url",
            "vcs_url",
            "copyright",
            "holder",
            "declared_license_expression",
            "declared_license_expression_spdx",
            "license_detections",
            "other_license_expression",
            "other_license_expression_spdx",
            "other_license_detections",
            "extracted_license_statement",
            "notice_text",
            "source_packages",
            "extra_data",
            "dependencies",
            "package_uid",
            "datasource_id",
            "purl",
            "repository_homepage_url",
            "repository_download_url",
            "api_data_url",
            "file_references",
        )

    def get_package_content(self, obj):
        return obj.get_package_content_display()


class PackageSetAPISerializer(ModelSerializer):
    packages = PackageAPISerializer(many=True)

    class Meta:
        model = PackageSet
        fields = [
            "uuid",
            "packages",
        ]


class PackageWatchAPISerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="api:packagewatch-detail", lookup_field="package_url")

    class Meta:
        model = PackageWatch
        fields = [
            "url",
            "package_url",
            "is_active",
            "depth",
            "watch_interval",
            "creation_date",
            "last_watch_date",
            "watch_error",
            "schedule_work_id",
        ]


class PackageWatchCreateSerializer(ModelSerializer):
    class Meta:
        model = PackageWatch
        fields = ["package_url", "depth", "watch_interval", "is_active"]
        extra_kwargs = {
            field: {"initial": PackageWatch._meta.get_field(field).get_default()}
            for field in ["depth", "watch_interval", "is_active"]
        }


class PackageWatchUpdateSerializer(ModelSerializer):
    class Meta:
        model = PackageWatch
        fields = ["depth", "watch_interval", "is_active"]


class CommaListField(ListField):
    """ListField that allows also a str of comma-separated values as value."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            split_data = []
            for datum in data:
                split_data.extend(datum.split(","))
            data = split_data
        return super().to_internal_value(data)


class CollectPackageSerializer(Serializer):
    purl = CharField(help_text="PackageURL strings in canonical form.")
    source_purl = CharField(
        required=False,
        help_text="Source PackageURL.",
    )
    addon_pipelines = ListField(
        child=CharField(),
        required=False,
        allow_empty=True,
        help_text="Addon pipelines to run on the package.",
    )
    sort = CommaListField(
        required=False,
        help_text="Fields to sort Package results by.",
    )

    def validate_purl(self, value):
        try:
            PackageURL.from_string(value)
        except ValueError as e:
            raise ValidationError(f"purl validation error: {e}")
        return value

    def validate_source_purl(self, value):
        if value:
            try:
                PackageURL.from_string(value)
            except ValueError as e:
                raise ValidationError(f"purl validation error: {e}")
        return value

    def validate_addon_pipelines(self, value):
        if invalid_pipelines := [pipe for pipe in value if not is_supported_addon_pipeline(pipe)]:
            raise ValidationError(
                f"Error unsupported addon pipelines: {','.join(invalid_pipelines)}"
            )
        return value

    def validate_sort(self, value):
        if invalid_sort_fields := [field for field in value if not is_supported_sort_field(field)]:
            raise ValidationError(f"Error unsupported sort fields: {','.join(invalid_sort_fields)}")
        return value


class PackageVersSerializer(Serializer):
    purl = CharField()
    vers = CharField(required=False)

    source_purl = CharField(required=False)
    addon_pipelines = ListField(
        required=False,
        allow_empty=True,
        help_text="Addon pipelines to run on the package.",
    )


class PackageUpdateSerializer(Serializer):
    purl = CharField(required=True)
    content_type = CharField(required=True)


class UpdatePackagesSerializer(Serializer):
    purls = PackageUpdateSerializer(many=True)
    uuid = CharField(required=False)


class IndexPackagesSerializer(Serializer):
    packages = PackageVersSerializer(many=True)
    reindex = BooleanField(default=False)
    reindex_set = BooleanField(default=False)


class PurlUpdateResponseSerializer(Serializer):
    purl = CharField()
    update_status = CharField()


class IndexPackagesResponseSerializer(Serializer):
    queued_packages_count = IntegerField(
        help_text="Number of package urls placed on the index queue."
    )
    queued_packages = ListField(
        child=CharField(),
        help_text="List of package urls that were placed on the index queue.",
    )
    requeued_packages_count = IntegerField(
        help_text="Number of existing package urls placed on the rescan queue."
    )
    requeued_packages = ListField(
        child=CharField(),
        help_text="List of existing package urls that were placed on the rescan queue.",
    )
    unqueued_packages_count = IntegerField(
        help_text="Number of package urls not placed on the index queue."
    )
    unqueued_packages = ListField(
        child=CharField(),
        help_text="List of package urls that were not placed on the index queue.",
    )
    unsupported_packages_count = IntegerField(
        help_text="Number of package urls that are not processable by the index queue."
    )
    unsupported_packages = ListField(
        child=CharField(),
        help_text="List of package urls that are not processable by the index queue.",
    )
    unsupported_vers_count = IntegerField(
        help_text="Number of vers range that are not supported by the univers or package_manager."
    )
    unsupported_vers = ListField(
        child=CharField(),
        help_text="List of vers range that are not supported by the univers or package_manager.",
    )


class PurlValidateResponseSerializer(Serializer):
    valid = BooleanField()
    exists = BooleanField(required=False)
    message = CharField()
    purl = CharField()


class PurlValidateSerializer(Serializer):
    purl = CharField(required=True)
    check_existence = BooleanField(required=False, default=False)


class GoLangPurlSerializer(Serializer):
    go_package = CharField(required=True)


class GoLangPurlResponseSerializer(Serializer):
    package_url = CharField()


class PurltoGitRepoSerializer(Serializer):
    package_url = CharField(required=True)


class PurltoGitRepoResponseSerializer(Serializer):
    git_repo = CharField(required=True)


def is_supported_addon_pipeline(addon_pipeline):
    from minecode.model_utils import SUPPORTED_ADDON_PIPELINES

    return addon_pipeline in SUPPORTED_ADDON_PIPELINES


def is_supported_sort_field(field):
    from packagedb.api import PACKAGE_FILTER_SORT_FIELDS

    # A field could have a leading `-`
    return field.lstrip("-") in PACKAGE_FILTER_SORT_FIELDS


class PackageActivitySerializer(ModelSerializer):
    url = HyperlinkedIdentityField(view_name="api:packageactivity-detail", lookup_field="uuid")

    class Meta:
        model = PackageActivity
        fields = [
            "url",
            "author",
            "content",
            "activity_update_date",
            "creation_date",
            "is_processed",
        ]


class HealthCommitRangeSerializer(Serializer):
    """Commit range analyzed by Healthycode (``commitMetadata``)."""

    first_commit = CharField(
        allow_null=True,
        required=False,
        help_text="First commit hash within the analyzed period.",
    )
    last_commit = CharField(
        allow_null=True,
        required=False,
        help_text="Last commit hash within the analyzed period.",
    )
    first_commit_date = CharField(
        allow_null=True,
        required=False,
        help_text="ISO datetime of the first commit in the analyzed period.",
    )
    last_commit_date = CharField(
        allow_null=True,
        required=False,
        help_text="ISO datetime of the last commit in the analyzed period.",
    )


class HealthMetricsSerializer(Serializer):
    """Healthycode project-health metrics object returned on ``metrics``."""

    total_commits = IntegerField(
        min_value=0,
        help_text=(
            "Number of commits per repository: activity for the Git repository "
            "analyzed, within the analyzed period."
        ),
    )
    total_contributors = IntegerField(
        min_value=0,
        help_text=(
            "Number of developers per repository: unique participants producing "
            "commits in the repository."
        ),
    )
    total_organizations = IntegerField(
        min_value=0,
        help_text=(
            "Number of contributing organizations whose members made contributions "
            "over the analyzed period. Organization is determined from the commit "
            "author email address."
        ),
    )
    pony_factor = IntegerField(
        min_value=0,
        help_text=(
            "Number of individuals who produce up to the first 50% of commits "
            "(descending). A low value means high dependency on those people "
            "(lottery / bus / contributor absence factor)."
        ),
    )
    elephant_factor = IntegerField(
        min_value=0,
        help_text=(
            "Number of unique organizations producing up to the first 50% of "
            "commits. Applies the pony factor to organizations (Bitergia)."
        ),
    )
    recent_organizations = IntegerField(
        min_value=0,
        help_text="Unique organizations with contributions in the last 90 days.",
    )
    recent_contributors = IntegerField(
        min_value=0,
        help_text="Unique individuals who contributed in the last 90 days.",
    )
    recent_commits = IntegerField(
        min_value=0,
        help_text="Commits made to the project in the last 90 days.",
    )
    contributor_growth = IntegerField(
        help_text=(
            "Growth of active contributors between the two halves of the analyzed "
            "period (second-half count minus first-half count). Can be negative."
        ),
    )
    contributor_growth_rate = FloatField(
        help_text=(
            "Growth rate of active contributors between the two halves of the "
            "analyzed period. Can be negative."
        ),
    )
    active_branches = IntegerField(
        min_value=0,
        help_text="Git branches with recent development activity (new commits).",
    )
    days_since_last_commit = IntegerField(
        min_value=0,
        help_text=("Days since the last commit. 99999 is used when there is no last-commit date."),
    )
    casual_regular_contributors_rate = FloatField(
        min_value=0,
        help_text=(
            "Ratio of casual contributors to core-plus-regular contributors "
            "(occasional vs regular contributors)."
        ),
    )
    returning_contributors = IntegerField(
        min_value=0,
        help_text=(
            "Unique individuals active in the last 90 days who also contributed "
            "in a previous period (retention)."
        ),
    )
    commits_over_periods_rate = FloatField(
        min_value=0,
        help_text="Rate of commits between the last 90 days and the last year.",
    )
    coefficient_of_variation = FloatField(
        min_value=0,
        help_text="Coefficient of variation of commits per month (std / mean).",
    )
    file_types_code = IntegerField(
        min_value=0,
        help_text="Touched files classified as code.",
    )
    file_types_binary = IntegerField(
        min_value=0,
        help_text="Touched files classified as binary.",
    )
    file_types_other = IntegerField(
        min_value=0,
        help_text="Touched files that are neither code nor binary.",
    )
    commit_size_added_lines = IntegerField(
        min_value=0,
        help_text="Total lines added across analyzed commits.",
    )
    commit_size_removed_lines = IntegerField(
        min_value=0,
        help_text="Total lines removed across analyzed commits.",
    )
    message_size_total = IntegerField(
        min_value=0,
        help_text="Sum of character lengths of analyzed commit messages.",
    )
    message_size_mean = FloatField(
        min_value=0,
        help_text="Mean character length of analyzed commit messages.",
    )
    message_size_median = IntegerField(
        min_value=0,
        help_text="Median character length of analyzed commit messages.",
    )
    developer_categories_core = IntegerField(
        min_value=0,
        help_text="Number of core contributors.",
    )
    developer_categories_regular = IntegerField(
        min_value=0,
        help_text="Number of regular contributors.",
    )
    developer_categories_casual = IntegerField(
        min_value=0,
        help_text="Number of casual contributors.",
    )
    commits_per_week = FloatField(
        allow_null=True,
        min_value=0,
        help_text="Mean commits per week. Null when the period is shorter than 7 days.",
    )
    commits_per_month = FloatField(
        allow_null=True,
        min_value=0,
        help_text="Mean commits per month. Null when the period is shorter than 30 days.",
    )
    commits_per_year = FloatField(
        allow_null=True,
        min_value=0,
        help_text="Mean commits per year. Null when the period is shorter than 365 days.",
    )
    found_file_license = IntegerField(
        min_value=0,
        max_value=1,
        help_text=(
            "1 if LICENSE, LICENSE.md, LICENSE.txt, or COPYING exists at the "
            "repository root, else 0."
        ),
    )
    found_file_adopters = IntegerField(
        min_value=0,
        max_value=1,
        help_text=(
            "1 if ADOPTERS, ADOPTERS.md, or ADOPTERS.txt exists at the repository root, else 0."
        ),
    )


class HealthPendingSerializer(Serializer):
    """HTTP 202 body while ``scan_repo_health`` is queued or in progress."""

    purl = CharField(help_text="Requested versionless npm Package-URL.")
    source_purl = CharField(help_text="Scanned versionless source Package-URL.")
    status = CharField(
        help_text="ScannableURI scan status, for example new, submitted, or in progress.",
    )


class HealthErrorSerializer(Serializer):
    """HTTP 400/500 error body from ``GET /api/health/``."""

    error = CharField(help_text="Error message.")


@extend_schema_field(HealthCommitRangeSerializer)
class HealthCommitRangeField(JSONField):
    pass


@extend_schema_field(HealthMetricsSerializer)
class HealthMetricsField(JSONField):
    pass


class PackageHealthMetricsSerializer(ModelSerializer):
    purl = CharField(
        source="package.package_url",
        read_only=True,
        help_text="Versionless npm Package-URL these metrics belong to.",
    )
    source_purl = CharField(
        source="source_package.package_url",
        read_only=True,
        help_text="Versionless source repository Package-URL that was scanned.",
    )
    vcs_url = CharField(
        read_only=True,
        help_text="VCS clone URL reported by the health scan.",
    )
    scoring_model = CharField(
        read_only=True,
        help_text='Scoring model identifier, for example "npm-health-0.2".',
    )
    score = FloatField(
        read_only=True,
        help_text=(
            "Overall health score from 0.0 (healthy) to 1.0 (unhealthy), as "
            "reported by Healthycode."
        ),
    )
    commit_range = HealthCommitRangeField(
        read_only=True,
        help_text="Commit range analyzed by the health scan.",
    )
    run_start_date = DateTimeField(
        read_only=True,
        help_text="When the health scan analysis window started.",
    )
    run_end_date = DateTimeField(
        read_only=True,
        help_text="When the health scan analysis window ended.",
    )
    metrics = HealthMetricsField(
        read_only=True,
        help_text="Healthycode project-health metrics for the scanned repository.",
    )
    date_collected = DateTimeField(
        read_only=True,
        help_text="When PurlDB stored these metrics.",
    )

    class Meta:
        model = PackageHealthMetrics
        fields = [
            "purl",
            "source_purl",
            "vcs_url",
            "scoring_model",
            "score",
            "commit_range",
            "run_start_date",
            "run_end_date",
            "metrics",
            "date_collected",
        ]


def validate_versionless_npm_purl(value):
    """
    Validate that ``value`` is a supported, valid Package-URL string
    e.g, for now an "npm" PURL without a version.
    """
    try:
        package_url = PackageURL.from_string(value)
    except ValueError as e:
        raise ValidationError(f"purl validation error: {e}")
    if package_url.type != "npm":
        raise ValidationError(
            f"The 'purl' {package_url!s} must use an 'npm' Package-URL type, not: {package_url.type!r}."
        )
    if package_url.version:
        raise ValidationError(
            f"The 'purl' {package_url!s} must not have a version: {package_url.version!r}."
        )
    return value


class PackageHealthMetricsRequestSerializer(Serializer):
    purl = CharField(
        required=True,
        help_text="PURL without a version.",
    )

    def validate_purl(self, value):
        return validate_versionless_npm_purl(value)
