#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import logging
import sys
import uuid
import natsort

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from packageurl.contrib.django.models import PackageURLMixin
from packageurl.contrib.django.models import PackageURLQuerySetMixin


TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def sort_version(packages):
    """
    Return the packages sorted by version.
    """
    return natsort.natsorted(packages, key=lambda p: p.version.replace('.', '~')+'z')


class PackageQuerySet(PackageURLQuerySetMixin, models.QuerySet):
    def insert(self, download_url, **extra_fields):
        """
        Create and return a new Package.
        Return None if the insertion failed when an identical entry already exist.
        """
        package, created = self.get_or_create(download_url=download_url, defaults=extra_fields)
        if created:
            return package


VCS_CHOICES = [
    ('git', 'git'),
    ('svn', 'subversion'),
    ('hg', 'mercurial'),
    ('bzr', 'bazaar'),
    ('cvs', 'cvs'),
]


class LowerCaseField(models.CharField):
    def __init__(self, *args, **kwargs):
        super(LowerCaseField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        return str(value).lower()


class HistoryMixin(models.Model):
    """
    A mixin with a simple text-based append-only history field.
    Each line in that text field is an history entry in the format:
    <timestamp><one space><message> string on a single line.
    """
    history = models.TextField(
        blank=True,
        editable=False,
        help_text=_(
            'History for this object a text where each line has the form: '
            '"<timestamp><one space><message>". Append-only and not editable.'),
    )

    class Meta:
        abstract = True

    def append_to_history(self, message, save=False):
        """
        Append the ``message`` string to the history of this object.
        """
        timestamp = timezone.now().strftime("%Y-%m-%d-%H:%M:%S")
        message = message.strip()
        if any(lf in message for lf in ('\n' , '\r')):
            raise ValueError('message cannot contain line returns (either CR or LF).')
        entry = f"{timestamp} {message}\n"
        self.history = self.history + entry

        if save:
            self.save()

    def get_history(self):
        """
        Return a list of mappings of all history entries from oldest to newest as:
            {"timestamp": "<YYYY-MM-DD-HH:MM:SS>", "message": "message"}
        """
        entries = (entry.partition(' ') for entry in self.history.strip().splitlines(False))
        return [{"timestamp": ts, "message": message} for ts, _, message in entries]


# TODO: Figure out what ordering we want for the fields
class AbstractPackage(PackageURLMixin, HistoryMixin, models.Model):
    """
    WARNING: Fields in this model are used in other Package models such as
    ScanCode toolkit and ScanCode.io. When updating these (in particular
    renaming) please ensure that you do not create problems and creafully
    synchornize changes.

    Most fields from this model are originally from ScanCode
    """
    uuid = models.UUIDField(
        verbose_name=_('UUID'),
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    type = LowerCaseField(
        max_length=16,
    )

    namespace = LowerCaseField(
        max_length=255,
    )

    name = LowerCaseField(
        max_length=100,
    )

    version = LowerCaseField(
        max_length=100,
    )

    qualifiers = LowerCaseField(
        max_length=1024,
    )

    subpath = LowerCaseField(
        max_length=200,
    )

    last_modified_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Timestamp set when a Package is created or modified'),
    )

    # FIXME: Sync with ScanCode, use file_name
    filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('File name of a Resource sometimes part of the URI proper'
                    'and sometimes only available through an HTTP header.'),
    )

    mining_level = models.PositiveIntegerField(
        default=0,
        help_text=_('A numeric indication of the highest depth and breadth '
                    'of package data collected through previous visits. '
                    'Higher means more and deeper collection.'),
    )

    primary_language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Primary programming language'),
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text=_('Description for this package. '
                    'By convention the first line should be a summary when available.')
    )

    release_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_('The date that the package file was created, or when '
                    'it was posted to its original download source.'),
    )

    keywords = ArrayField(
        base_field=models.TextField(
            blank=True,
            null=True,
        ),
        default=list,
        blank=True,
        null=True,
        help_text=_('A list of keywords.'),
    )

    homepage_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('URL to the homepage for this package.'),
    )

    download_url = models.CharField(
        max_length=2048,
        unique=True,
        db_index=True,
        help_text=_('A direct download URL.'),
    )

    size = models.BigIntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_('Size in bytes.'),
    )

    sha1 = models.CharField(
        verbose_name=_('download SHA1'),
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('SHA1 checksum hex-encoded, as in sha1sum.'),
    )

    md5 = models.CharField(
        verbose_name=_('download MD5'),
        max_length=32,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('MD5 checksum hex-encoded, as in md5sum.'),
    )

    sha256 = models.CharField(
        verbose_name=_('download SHA256'),
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('SHA256 checksum hex-encoded, as in sha256sum.'),
    )

    sha512 = models.CharField(
        verbose_name=_('download SHA512'),
        max_length=128,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('SHA512 checksum hex-encoded, as in sha512sum.'),
    )

    bug_tracking_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('URL to the issue or bug tracker for this package')
    )

    code_view_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('a URL where the code can be browsed online')
    )

    vcs_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('a URL to the VCS repository in the SPDX form of: '
                    '"git", "svn", "hg", "bzr", "cvs", '
                    'https://github.com/nexb/scancode-toolkit.git@405aaa4b3 '
                    'See SPDX specification "Package Download Location" '
                    'at https://spdx.org/spdx-specification-21-web-version#h.49x2ik5 ')
    )

    copyright = models.TextField(
        blank=True,
        null=True,
        help_text=_('Copyright statements for this package. Typically one per line.'),
    )

    license_expression = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('The normalized license expression for this package as derived '
                    'from its declared license.')
    )

    declared_license = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('The declared license mention or tag or text as found in a '
                    'package manifest.')
    )

    notice_text = models.TextField(
        blank=True,
        null=True,
        help_text=_('A notice text for this package.')
    )

    root_path = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('The path to the root of the package documented in this manifest '
                    'if any, such as a Maven .pom or a npm package.json parent '
                    'directory.')
    )

    contains_source_code = models.BooleanField(
        null=True,
        blank=True,
    )

    source_packages = ArrayField(
        base_field=models.TextField(
            blank=True,
            null=True,
        ),
        default=list,
        blank=True,
        null=True,
        help_text=_('A list of source package URLs (aka. "purl") for this package. '
                    'For instance an SRPM is the "source package" for a binary RPM.'),
    )

    extra_data = models.JSONField(
        blank=True,
        default=dict,
        help_text=_('An optional JSON-formatted field to identify additional package attributes.'),
    )

    search_vector = SearchVectorField(null=True)

    class Meta:
        abstract = True


# TODO: Figure out what ordering we want for the fields
class Package(AbstractPackage):
    objects = PackageQuerySet.as_manager()

    # TODO: Think about ordering, unique together, indexes, etc.
    class Meta:
        ordering = ['id']
        indexes = [
            # GIN index for search performance increase
            GinIndex(fields=['search_vector']),
            # multicolumn index for search on a whole `purl`
            models.Index(fields=[
                'type', 'namespace', 'name', 'version', 'qualifiers', 'subpath'
            ]),
            models.Index(fields=['type']),
            models.Index(fields=['namespace']),
            models.Index(fields=['name']),
            models.Index(fields=['version']),
            models.Index(fields=['qualifiers']),
            models.Index(fields=['subpath']),
            models.Index(fields=['download_url']),
            models.Index(fields=['filename']),
            models.Index(fields=['size']),
            models.Index(fields=['release_date'])
        ]

    def __str__(self):
        return self.package_url

    def to_dict(self):
        from packagedb.serializers import PackageMetadataSerializer
        package_metadata = PackageMetadataSerializer(self).data
        return package_metadata

    def get_all_versions(self):
        """
        Return a list of all the versions of this Package.
        """
        manager = self.__class__.objects
        queryset = manager.filter(
            name=self.name,
            type=self.type,
            namespace=self.namespace,
        )
        return queryset

    def get_latest_version(self):
        """
        Return the latest version of this Package.
        """
        sorted_versions = sort_version(self.get_all_versions())
        if sorted_versions:
            return sorted_versions[-1]


# TODO: Sync with the same definition in other tools
# and same case for everything. We will need to check organization.models.Owner's OWNER_TYPE_CHOICES
party_person = 'person'
# often loosely defined
party_project = 'project'
# more formally defined
party_org = 'organization'
PARTY_TYPES = (
    (party_person, party_person),
    (party_project, party_project),
    (party_org, party_org),
)


class Party(models.Model):
    """
    A party is a person, project or organization related to a package.
    """
    package = models.ForeignKey(
        Package,
        related_name='parties',
        on_delete=models.CASCADE,
        help_text=_('The Package that this party is related to')
    )

    type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=PARTY_TYPES,
        help_text=_('the type of this party')
    )

    role = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_('A role for this party. Something such as author, '
                    'maintainer, contributor, owner, packager, distributor, '
                    'vendor, developer, owner, etc.')
    )

    name = models.CharField(
        max_length=70,
        blank=True,
        null=True,
        help_text=_('Name of this party.')
    )

    email = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Email for this party.')
    )

    url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('URL to a primary web page for this party.')
    )


class DependentPackage(models.Model):
    """
    An identifiable dependent package package object.
    """
    package = models.ForeignKey(
        Package,
        related_name='dependencies',
        on_delete=models.CASCADE,
        help_text=_('The Package that this dependent package is related to')
    )

    purl = models.CharField(
        max_length=2048,
        blank=True,
        null=True,
        help_text=_('A compact purl package URL')
    )

    requirement = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('A string defining version(s)requirements. Package-type specific.')
    )

    scope = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('The scope of this dependency, such as runtime, install, etc. '
                    'This is package-type specific and is the original scope string.')
    )

    is_runtime = models.BooleanField(
        default=True,
        help_text=_('True if this dependency is a runtime dependency.')
    )

    is_optional = models.BooleanField(
        default=False,
        help_text=_('True if this dependency is an optional dependency')
    )

    is_resolved = models.BooleanField(
        default=False,
        help_text=_('True if this dependency version requirement has '
                    'been resolved and this dependency url points to an '
                    'exact version.')
    )


class AbstractResource(models.Model):
    """
    These model fields should be kept in line with scancode.resource.Resource
    """

    path = models.CharField(
        max_length=2000,
        help_text=_('The full path value of a resource (file or directory) in the archive it is from.'),
    )

    size = models.BigIntegerField(
        blank=True,
        null=True,
        help_text=_('Size in bytes.'),
    )

    sha1 = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text=_('SHA1 checksum hex-encoded, as in sha1sum.'),
    )

    md5 = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_('MD5 checksum hex-encoded, as in md5sum.'),
    )

    sha256 = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text=_('SHA256 checksum hex-encoded, as in sha256sum.'),
    )

    sha512 = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text=_('SHA512 checksum hex-encoded, as in sha512sum.'),
    )

    git_sha1 = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text=_('git SHA1 checksum hex-encoded'),
    )

    is_file = models.BooleanField(
        default=False,
        help_text=_('True if this Resource is a file, False if it is a Directory')
    )

    copyright = models.TextField(
        blank=True,
        null=True,
        help_text=_('Copyright statements detected in this Resource'),
    )

    license_expression = models.CharField(
        max_length=8192,
        blank=True,
        null=True,
        help_text=_('The combined and normalized license expression for this Resource as derived '
                    'from its detected license expressions')
    )

    extra_data = models.JSONField(
        blank=True,
        default=dict,
        help_text=_('An optional JSON-formatted field to identify additional resource attributes.'),
    )

    @property
    def type(self):
        return 'file' if self.is_file else 'directory'

    @type.setter
    def type(self, value):
        if value == 'file':
            self.is_file = True
        else:
            self.is_file = False

    def __str__(self):
        return self.path

    class Meta:
        abstract = True


class Resource(AbstractResource):
    package = models.ForeignKey(
        Package,
        related_name='resources',
        on_delete=models.CASCADE,
        help_text=_('The Package that this Resource is from')
    )

    extra_data = models.JSONField(
        blank=True,
        default=dict,
        help_text=_('An optional JSON-formatted field to identify additional resource attributes.'),
    )

    class Meta:
        unique_together = (
            ('package', 'path'),
        )
        ordering = ('package', 'path')



# FIXME: This is not clearly specified and needs to be reworked.
# class PackageRelationship(models.Model):
#     """
#     A directed relationship between two packages.

#     This consists of three attributes:
#     - The "from" (or subject) package "purl" in the relationship,
#     - the "to" (or object) package "purl" in the relationship,
#     - and the "relationship" (or predicate) string that specifies the relationship.
#     """
#     package = models.ForeignKey(
#         Package,
#         help_text='The Package that this package relationship is related to'
#     )

#     from_purl = models.CharField(
#         max_length=2048,
#         blank=True,
#         null=True,
#         help_text='A compact purl package URL.'
#     )

#     relationship = models.CharField(
#         max_length=2048,
#         blank=True,
#         null=True,
#         help_text='Relationship between the from and to package '
#                   'URLs such as "source_of" when a package is the source '
#                   'code package for another package.'
#     )

#     to_purl = models.CharField(
#         max_length=2048,
#         blank=True,
#         null=True,
#         help_text='A compact purl package URL.'
#     )
