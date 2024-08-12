#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.urls import reverse_lazy

from packageurl import PackageURL
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BooleanField
from rest_framework.serializers import CharField
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
from packagedb.models import PackageSet
from packagedb.models import PackageWatch
from packagedb.models import Party
from packagedb.models import Resource


class ResourceAPISerializer(HyperlinkedModelSerializer):
    package = HyperlinkedRelatedField(
        view_name='api:package-detail', lookup_field='uuid', read_only=True)
    purl = CharField(source='package.package_url')

    class Meta:
        model = Resource
        fields = (
            'package',
            'purl',
            'path',
            'type',
            'name',
            'extension',
            'size',
            'md5',
            'sha1',
            'sha256',
            'sha512',
            'git_sha1',
            'mime_type',
            'file_type',
            'programming_language',
            'is_binary',
            'is_text',
            'is_archive',
            'is_media',
            'is_key_file',
            'detected_license_expression',
            'detected_license_expression_spdx',
            'license_detections',
            'license_clues',
            'percentage_of_license_text',
            'copyrights',
            'holders',
            'authors',
            'package_data',
            'emails',
            'urls',
            'extra_data',
        )
        read_only_fields = fields


class ResourceMetadataSerializer(HyperlinkedModelSerializer):
    for_packages = JSONField()

    class Meta:
        model = Resource
        fields = (
            'path',
            'type',
            'name',
            'extension',
            'size',
            'md5',
            'sha1',
            'sha256',
            'sha512',
            'git_sha1',
            'mime_type',
            'file_type',
            'programming_language',
            'is_binary',
            'is_text',
            'is_archive',
            'is_media',
            'is_key_file',
            'detected_license_expression',
            'detected_license_expression_spdx',
            'license_detections',
            'license_clues',
            'percentage_of_license_text',
            'copyrights',
            'holders',
            'authors',
            'package_data',
            'for_packages',
            'emails',
            'urls',
            'extra_data',
        )


class PartySerializer(ModelSerializer):
    class Meta:
        model = Party
        fields = (
            'type',
            'role',
            'name',
            'email',
            'url',
        )


class DependentPackageSerializer(ModelSerializer):
    class Meta:
        model = DependentPackage
        fields = (
            'purl',
            'extracted_requirement',
            'scope',
            'is_runtime',
            'is_optional',
            'is_resolved',
        )


class PackageInPackageSetAPISerializer(ModelSerializer):
    """
    This serializes Package instances within a PackageSet that is within a
    Package in the PackageAPISerializer
    """
    class Meta:
        model = Package
        fields = (
            'uuid',
        )

    def to_representation(self, instance):
        reverse_uri = reverse_lazy(
            'api:package-detail', kwargs={'uuid': instance.uuid})
        request = self.context['request']
        return request.build_absolute_uri(reverse_uri)


class PackageSetAPISerializer(ModelSerializer):
    packages = PackageInPackageSetAPISerializer(many=True)

    class Meta:
        model = PackageSet
        fields = (
            'uuid',
            'packages',
        )


class PackageAPISerializer(HyperlinkedModelSerializer):
    dependencies = DependentPackageSerializer(many=True)
    parties = PartySerializer(many=True)
    resources = HyperlinkedIdentityField(
        view_name='api:package-resources', lookup_field='uuid')
    history = HyperlinkedIdentityField(
        view_name='api:package-history', lookup_field='uuid')
    url = HyperlinkedIdentityField(
        view_name='api:package-detail', lookup_field='uuid')
    package_sets = PackageSetAPISerializer(many=True)
    package_content = SerializerMethodField()
    declared_license_expression_spdx = CharField()
    other_license_expression_spdx = CharField()

    class Meta:
        model = Package
        fields = (
            'url',
            'uuid',
            'filename',
            'package_sets',
            'package_content',
            'purl',
            'type',
            'namespace',
            'name',
            'version',
            'qualifiers',
            'subpath',
            'primary_language',
            'description',
            'release_date',
            'parties',
            'keywords',
            'homepage_url',
            'download_url',
            'bug_tracking_url',
            'code_view_url',
            'vcs_url',
            'repository_homepage_url',
            'repository_download_url',
            'api_data_url',
            'size',
            'md5',
            'sha1',
            'sha256',
            'sha512',
            'copyright',
            'holder',
            'declared_license_expression',
            'declared_license_expression_spdx',
            'license_detections',
            'other_license_expression',
            'other_license_expression_spdx',
            'other_license_detections',
            'extracted_license_statement',
            'notice_text',
            'source_packages',
            'extra_data',
            'package_uid',
            'datasource_id',
            'file_references',
            'dependencies',
            'resources',
            'history',
        )
        read_only_fields = fields

    def get_package_content(self, obj):
        return obj.get_package_content_display()


class PackageInPackageSetMetadataSerializer(ModelSerializer):
    """
    This serializes Package instances within a PackageSet that is within a
    Package in the PackageMetadataSerializer
    """
    class Meta:
        model = Package
        fields = (
            'uuid',
        )

    def to_representation(self, instance):
        return instance.package_uid


class PackageSetMetadataSerializer(ModelSerializer):
    packages = PackageInPackageSetMetadataSerializer(many=True)

    class Meta:
        model = PackageSet
        fields = (
            'uuid',
            'packages',
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
            'type',
            'namespace',
            'name',
            'version',
            'qualifiers',
            'subpath',
            'package_sets',
            'package_content',
            'primary_language',
            'description',
            'release_date',
            'parties',
            'keywords',
            'homepage_url',
            'download_url',
            'size',
            'md5',
            'sha1',
            'sha256',
            'sha512',
            'bug_tracking_url',
            'code_view_url',
            'vcs_url',
            'copyright',
            'holder',
            'declared_license_expression',
            'declared_license_expression_spdx',
            'license_detections',
            'other_license_expression',
            'other_license_expression_spdx',
            'other_license_detections',
            'extracted_license_statement',
            'notice_text',
            'source_packages',
            'extra_data',
            'dependencies',
            'package_uid',
            'datasource_id',
            'purl',
            'repository_homepage_url',
            'repository_download_url',
            'api_data_url',
            'file_references',
        )

    def get_package_content(self, obj):
        return obj.get_package_content_display()


class PackageSetAPISerializer(ModelSerializer):
    packages = PackageAPISerializer(many=True)

    class Meta:
        model = PackageSet
        fields = [
            'uuid',
            'packages',
        ]


class PackageWatchAPISerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(
        view_name='api:packagewatch-detail',
        lookup_field='package_url'
    )

    class Meta:
        model = PackageWatch
        fields = [
            'url',
            'package_url',
            'is_active',
            'depth',
            'watch_interval',
            'creation_date',
            'last_watch_date',
            'watch_error',
            'schedule_work_id',
        ]


class PackageWatchCreateSerializer(ModelSerializer):
    class Meta:
        model = PackageWatch
        fields = ["package_url", "depth", "watch_interval", "is_active"]
        extra_kwargs = {
            field: {"initial": PackageWatch._meta.get_field(
                field).get_default()}
            for field in ["depth", "watch_interval", "is_active"]
        }


class PackageWatchUpdateSerializer(ModelSerializer):
    class Meta:
        model = PackageWatch
        fields = ['depth', 'watch_interval', 'is_active']


class CommaListField(ListField):
    """ListField that allows also a str of comma-separated values as value."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            split_data = []
            for datum in data:
                split_data.extend(datum.split(','))
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
            raise ValidationError(f'purl validation error: {e}')
        return value

    def validate_source_purl(self, value):
        if value:
            try:
                PackageURL.from_string(value)
            except ValueError as e:
                raise ValidationError(f'purl validation error: {e}')
        return value

    def validate_addon_pipelines(self, value):
        if invalid_pipelines := [pipe for pipe in value if not is_supported_addon_pipeline(pipe)]:
            raise ValidationError(f'Error unsupported addon pipelines: {",".join(invalid_pipelines)}')
        return value

    def validate_sort(self, value):
        if invalid_sort_fields := [field for field in value if not is_supported_sort_field(field)]:
            raise ValidationError(f'Error unsupported sort fields: {",".join(invalid_sort_fields)}')
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
        help_text="Number of package urls placed on the index queue.")
    queued_packages = ListField(
        child=CharField(),
        help_text="List of package urls that were placed on the index queue."
    )
    requeued_packages_count = IntegerField(
        help_text="Number of existing package urls placed on the rescan queue.")
    requeued_packages = ListField(
        child=CharField(),
        help_text="List of existing package urls that were placed on the rescan queue."
    )
    unqueued_packages_count = IntegerField(
        help_text="Number of package urls not placed on the index queue.")
    unqueued_packages = ListField(
        child=CharField(),
        help_text="List of package urls that were not placed on the index queue."
    )
    unsupported_packages_count = IntegerField(
        help_text="Number of package urls that are not processable by the index queue.")
    unsupported_packages = ListField(
        child=CharField(),
        help_text="List of package urls that are not processable by the index queue."
    )
    unsupported_vers_count = IntegerField(
        help_text="Number of vers range that are not supported by the univers or package_manager.")
    unsupported_vers = ListField(
        child=CharField(),
        help_text="List of vers range that are not supported by the univers or package_manager."
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
    return field.lstrip('-') in PACKAGE_FILTER_SORT_FIELDS
