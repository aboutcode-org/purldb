#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from rest_framework.serializers import CharField
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from packagedb.models import DependentPackage
from packagedb.models import Package
from packagedb.models import Party
from packagedb.models import Resource


class ResourceAPISerializer(HyperlinkedModelSerializer):
    package = HyperlinkedRelatedField(view_name='api:package-detail', lookup_field='uuid', read_only=True)
    purl = CharField(source='package.package_url')

    class Meta:
        model = Resource
        fields = (
            'package',
            'purl',
            'path',
            'size',
            'sha1',
            'md5',
            'sha256',
            'sha512',
            'git_sha1',
            'is_file',
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
            'requirement',
            'scope',
            'is_runtime',
            'is_optional',
            'is_resolved',
        )


class PackageAPISerializer(HyperlinkedModelSerializer):
    parties = PartySerializer(many=True)
    dependencies = DependentPackageSerializer(many=True)
    url = HyperlinkedIdentityField(view_name='api:package-detail', lookup_field='uuid')
    resources = HyperlinkedIdentityField(view_name='api:package-resources', lookup_field='uuid')

    class Meta:
        model = Package
        fields = (
            'url',
            'uuid',
            'filename',
            'release_date',
            'type',
            'namespace',
            'name',
            'version',
            'qualifiers',
            'subpath',
            'primary_language',
            'description',
            'parties',
            'keywords',
            'homepage_url',
            'download_url',
            'size',
            'sha1',
            'md5',
            'sha256',
            'sha512',
            'bug_tracking_url',
            'code_view_url',
            'vcs_url',
            'copyright',
            'license_expression',
            'declared_license',
            'notice_text',
            'contains_source_code',
            'root_path',
            'dependencies',
            'source_packages',
            'package_url',
            'history',
            'resources',
            'extra_data',
        )


class PackageMetadataSerializer(ModelSerializer):
    """
    Serializes the metadata of a Package from the fields of the Package model
    such that the data returned is in the same form as a ScanCode Package scan.

    This differs from PackageSerializer used for the API by the addition of
    the `package_url` field and the exclusion of the `uuid`, and `filename` fields.
    """
    parties = PartySerializer(many=True)
    dependencies = DependentPackageSerializer(many=True)

    class Meta:
        model = Package
        fields = (
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
            'size',
            'sha1',
            'md5',
            'sha256',
            'sha512',
            'bug_tracking_url',
            'code_view_url',
            'vcs_url',
            'copyright',
            'license_expression',
            'declared_license',
            'notice_text',
            'root_path',
            'dependencies',
            'contains_source_code',
            'source_packages',
            'package_url',
        )
