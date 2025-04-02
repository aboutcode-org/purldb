#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import copy
import logging
import sys
import uuid
from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.models import UserManager
from django.contrib.postgres.fields import ArrayField
from django.core import exceptions
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import natsort
from aboutcode.federatedcode.contrib.django.models import (
    FederatedCodePackageActivityMixin,
)
from dateutil.parser import parse as dateutil_parse
from licensedcode.cache import build_spdx_license_expression
from packagedcode.models import normalize_qualifiers
from packageurl import PackageURL
from packageurl.contrib.django.models import PackageURLMixin
from packageurl.contrib.django.models import PackageURLQuerySetMixin
from rest_framework.authtoken.models import Token

from packagedb import schedules

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def sort_version(packages):
    """Return the packages sorted by version."""
    return natsort.natsorted(packages, key=lambda p: p.version.replace(".", "~") + "z")


class PackageQuerySet(PackageURLQuerySetMixin, models.QuerySet):
    def insert(self, download_url, **extra_fields):
        """
        Create and return a new Package.
        Return None if the insertion failed when an identical entry already exist.
        """
        package, created = self.get_or_create(
            download_url=download_url, defaults=extra_fields
        )
        if created:
            return package

    def get_or_none(self, *args, **kwargs):
        """Return the object matching the given lookup parameters, or None if no match exists."""
        try:
            return self.get(*args, **kwargs)
        except Package.DoesNotExist:
            return


VCS_CHOICES = [
    ("git", "git"),
    ("svn", "subversion"),
    ("hg", "mercurial"),
    ("bzr", "bazaar"),
    ("cvs", "cvs"),
]


class LowerCaseField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return str(value).lower()


class HistoryMixin(models.Model):
    """
    A mixin with a JSONField-based append-only history field. The history field
    is a list containing mappings representing the history for this object. Each
    mapping contains the field "timestamp" and "message".
    """

    history = models.JSONField(
        default=list,
        blank=True,
        editable=False,
        help_text=_(
            "A list of mappings representing the history for this object. "
            'Each mapping contains the fields "timestamp" and "message".'
        ),
    )
    created_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Timestamp set when a Package is created"),
    )
    last_modified_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Timestamp set when a Package is created or modified"),
    )

    class Meta:
        abstract = True

    def append_to_history(self, message, data={}, save=False):
        """Append the ``message`` string to the history of this object."""
        time = timezone.now()
        timestamp = time.strftime("%Y-%m-%d-%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "message": message,
            "data": data,
        }
        self.history.append(entry)
        self.last_modified_date = time

        if save:
            self.save()

    def get_history(self):
        """
        Return a list of mappings of all history entries from oldest to newest as:
            {"timestamp": "<YYYY-MM-DD-HH:MM:SS>", "message": "message"}
        """
        history_copy = copy.deepcopy(self.history)
        return history_copy


class HashFieldsMixin(models.Model):
    """
    The hash fields are not indexed by default, use the `indexes` in Meta as needed:
    class Meta:
        indexes = [
            models.Index(fields=['md5']),
            models.Index(fields=['sha1']),
            models.Index(fields=['sha256']),
            models.Index(fields=['sha512']),
        ]

    This model is from scancode.io.
    """

    md5 = models.CharField(
        _("MD5"),
        max_length=32,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("MD5 checksum hex-encoded, as in md5sum."),
    )
    sha1 = models.CharField(
        _("SHA1"),
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("SHA1 checksum hex-encoded, as in sha1sum."),
    )
    sha256 = models.CharField(
        _("SHA256"),
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("SHA256 checksum hex-encoded, as in sha256sum."),
    )
    sha512 = models.CharField(
        _("SHA512"),
        max_length=128,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("SHA512 checksum hex-encoded, as in sha512sum."),
    )

    class Meta:
        abstract = True


class ExtraDataFieldMixin(models.Model):
    """
    Adds the `extra_data` field and helper methods.

    This model is from scancode.io.
    """

    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Optional mapping of extra data key/values."),
    )

    def update_extra_data(self, data):
        """Update `extra_data` field with the provided `data` dict."""
        if type(data) is not dict:
            raise ValueError("Argument `data` value must be a dict()")

        self.extra_data.update(data)
        self.save()

    class Meta:
        abstract = True


class AbstractPackage(models.Model):
    """
    These model fields should be kept in line with `packagedcode.models.PackageData`.

    This model is from scancode.io.
    """

    filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=_(
            "File name of a Resource sometimes part of the URI proper"
            "and sometimes only available through an HTTP header."
        ),
    )
    primary_language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Primary programming language."),
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "Description for this package. "
            "By convention the first line should be a summary when available."
        ),
    )
    release_date = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_(
            "The date and time that the package file was created, or when "
            "it was posted to its original download source."
        ),
    )
    homepage_url = models.CharField(
        _("Homepage URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("URL to the homepage for this package."),
    )
    download_url = models.CharField(
        _("Download URL"),
        max_length=2048,
        unique=True,
        db_index=True,
        help_text=_("A direct download URL."),
    )
    size = models.BigIntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Size in bytes."),
    )
    bug_tracking_url = models.CharField(
        _("Bug tracking URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("URL to the issue or bug tracker for this package."),
    )
    code_view_url = models.CharField(
        _("Code view URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("a URL where the code can be browsed online."),
    )
    vcs_url = models.CharField(
        _("VCS URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_(
            "A URL to the VCS repository in the SPDX form of: "
            '"git", "svn", "hg", "bzr", "cvs", '
            "https://github.com/nexb/scancode-toolkit.git@405aaa4b3 "
            'See SPDX specification "Package Download Location" '
            "at https://spdx.org/spdx-specification-21-web-version#h.49x2ik5"
        ),
    )
    repository_homepage_url = models.CharField(
        _("Repository homepage URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_(
            "URL to the page for this package in its package repository. "
            "This is typically different from the package homepage URL proper."
        ),
    )
    repository_download_url = models.CharField(
        _("Repository download URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_(
            "Download URL to download the actual archive of code of this "
            "package in its package repository. "
            "This may be different from the actual download URL."
        ),
    )
    api_data_url = models.CharField(
        _("API data URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_(
            "API URL to obtain structured data for this package such as the "
            "URL to a JSON or XML api its package repository."
        ),
    )
    copyright = models.TextField(
        blank=True,
        null=True,
        help_text=_("Copyright statements for this package. Typically one per line."),
    )
    holder = models.TextField(
        blank=True,
        null=True,
        help_text=_("Holders for this package. Typically one per line."),
    )
    declared_license_expression = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "The license expression for this package typically derived "
            "from its extracted_license_statement or from some other type-specific "
            "routine or convention."
        ),
    )
    license_detections = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text=_(
            "A list of LicenseDetection mappings typically derived "
            "from its extracted_license_statement or from some other type-specific "
            "routine or convention."
        ),
    )
    other_license_expression = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "The license expression for this package which is different from the "
            "declared_license_expression, (i.e. not the primary license) "
            "routine or convention."
        ),
    )
    other_license_detections = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text=_(
            "A list of LicenseDetection mappings which is different from the "
            "declared_license_expression, (i.e. not the primary license) "
            "These are detections for the detection for the license expressions "
            "in other_license_expression. "
        ),
    )
    extracted_license_statement = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "The license statement mention, tag or text as found in a "
            "package manifest and extracted. This can be a string, a list or dict of "
            "strings possibly nested, as found originally in the manifest."
        ),
    )
    notice_text = models.TextField(
        blank=True,
        null=True,
        help_text=_("A notice text for this package."),
    )
    datasource_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text=_(
            "The identifier for the datafile handler used to obtain this package."
        ),
    )
    file_references = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text=_(
            "List of file paths and details for files referenced in a package "
            "manifest. These may not actually exist on the filesystem. "
            "The exact semantics and base of these paths is specific to a "
            "package type or datafile format."
        ),
    )

    class Meta:
        abstract = True

    @property
    def declared_license_expression_spdx(self):
        declared_license_expression = self.declared_license_expression
        if declared_license_expression:
            return build_spdx_license_expression(declared_license_expression)

    @property
    def other_license_expression_spdx(self):
        other_license_expression = self.other_license_expression
        if other_license_expression:
            return build_spdx_license_expression(other_license_expression)


class PackageContentType(models.IntegerChoices):
    """List of Package content types."""

    # TODO: curation is a special case, based on how the curation identity
    # fields matches with the current package
    CURATION = 1, "curation"
    PATCH = 2, "patch"
    SOURCE_REPO = 3, "source_repo"
    SOURCE_ARCHIVE = 4, "source_archive"
    BINARY = 5, "binary"
    TEST = 6, "test"
    DOC = 7, "doc"


def get_class_name(obj):
    """Return a string containing the class name of `obj`"""
    return type(obj).__name__


# TODO: Figure out what ordering we want for the fields
class Package(
    HistoryMixin,
    ExtraDataFieldMixin,
    HashFieldsMixin,
    PackageURLMixin,
    AbstractPackage,
):
    uuid = models.UUIDField(
        verbose_name=_("UUID"), default=uuid.uuid4, unique=True, editable=False
    )
    mining_level = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "A numeric indication of the highest depth and breadth "
            "of package data collected through previous visits. "
            "Higher means more and deeper collection."
        ),
    )
    keywords = ArrayField(
        base_field=models.TextField(
            blank=True,
            null=True,
        ),
        default=list,
        blank=True,
        null=True,
        help_text=_("A list of keywords."),
    )
    root_path = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_(
            "The path to the root of the package documented in this manifest "
            "if any, such as a Maven .pom or a npm package.json parent "
            "directory."
        ),
    )
    source_packages = ArrayField(
        base_field=models.TextField(
            blank=True,
            null=True,
        ),
        default=list,
        blank=True,
        null=True,
        help_text=_(
            'A list of source package URLs (aka. "purl") for this package. '
            'For instance an SRPM is the "source package" for a binary RPM.'
        ),
    )
    last_indexed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp set to the date of the last indexing. Used to track indexing status.",
    )
    index_error = models.TextField(
        null=True,
        blank=True,
        help_text="Indexing errors messages. When present this means the indexing has failed.",
    )
    package_sets = models.ManyToManyField(
        "PackageSet",
        related_name="packages",
        help_text=_("A set representing the Package sets this Package is a member of."),
    )
    package_content = models.IntegerField(
        null=True,
        choices=PackageContentType.choices,
        help_text=_(
            "Content of this Package as one of: {}".format(
                ", ".join(PackageContentType.labels)
            )
        ),
    )
    summary = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text=_(
            "A mapping containing a summary and license clarity score for this Package"
        ),
    )
    is_duplicate = models.BooleanField(
        default=False,
        help_text=_("True if this Package is a duplicate of another Package"),
    )

    objects = PackageQuerySet.as_manager()

    # TODO: Think about ordering, unique together, indexes, etc.
    class Meta:
        ordering = ["id"]
        unique_together = [
            (
                "download_url",
                "type",
                "namespace",
                "name",
                "version",
                "qualifiers",
                "subpath",
            )
        ]
        indexes = [
            # multicolumn index for search on a whole `purl`
            models.Index(
                fields=["type", "namespace", "name", "version", "qualifiers", "subpath"]
            ),
            models.Index(fields=["type"]),
            models.Index(fields=["namespace"]),
            models.Index(fields=["name"]),
            models.Index(fields=["version"]),
            models.Index(fields=["qualifiers"]),
            models.Index(fields=["subpath"]),
            models.Index(fields=["download_url"]),
            models.Index(fields=["filename"]),
            models.Index(fields=["size"]),
            models.Index(fields=["release_date"]),
            models.Index(fields=["md5"]),
            models.Index(fields=["sha1"]),
            models.Index(fields=["sha256"]),
            models.Index(fields=["sha512"]),
        ]

    def __str__(self):
        return self.package_url

    @property
    def purl(self):
        return self.package_url

    @property
    def package_uid(self):
        purl = PackageURL.from_string(self.package_url)
        purl.qualifiers["uuid"] = str(self.uuid)
        return str(purl)

    def to_dict(self):
        from packagedb.serializers import PackageMetadataSerializer

        package_metadata = PackageMetadataSerializer(self).data
        return package_metadata

    def get_all_versions(self):
        """Return a list of all the versions of this Package."""
        manager = self.__class__.objects
        queryset = manager.filter(
            name=self.name,
            type=self.type,
            namespace=self.namespace,
        )
        return queryset

    def get_latest_version(self):
        """Return the latest version of this Package."""
        sorted_versions = sort_version(self.get_all_versions())
        if sorted_versions:
            return sorted_versions[-1]

    def reindex(self, **kwargs):
        """
        Trigger another scan of this Package, where a new ScannableURI is
        created for this Package. The fingerprints and Resources associated with
        this Package are deleted and recreated from the updated scan data.
        """
        from minecode.model_utils import DEFAULT_PIPELINES
        from minecode.model_utils import add_package_to_scan_queue

        addon_pipelines = kwargs.get("addon_pipelines", [])
        pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)

        add_package_to_scan_queue(
            self, pipelines=pipelines, reindex_uri=True, priority=100
        )

    def update_fields(self, save=False, **values_by_fields):
        """
        Given keyword arguments from `values_by_fields`, where the argument
        names passed into the method are the fields of this Package to be
        updated and the values are the new values to be set (e.g.
        path="/new/path", sha1="newsha1"), update all the fields and return a
        2-tuple containing this Package and a list containing the fields that
        were updated.

        In the instance where the field to be updated is `dependencies`,
        `parties`, or `resources`, then we will delete all existing related
        models for that field and then create the new models from the argument
        values.
        """
        class_name = get_class_name(self)
        replaced_fields = []
        updated_fields = []
        history_entries = []
        for field, value in values_by_fields.items():
            if not hasattr(self, field):
                # Raise exception when we we are given a keyword argument that
                # doesn't correspond to a Package field
                raise AttributeError(f"'{class_name}' has no attribute '{field}'")

            related_model_fields = [
                "dependencies",
                "parties",
                "resources",
            ]
            if field in related_model_fields:
                unsaved_models = []
                if field == "dependencies":
                    for dep_data in value:
                        if isinstance(dep_data, dict | OrderedDict):
                            dep = DependentPackage(
                                package=self,
                                purl=dep_data.get("purl"),
                                extracted_requirement=dep_data.get(
                                    "extracted_requirement"
                                ),
                                scope=dep_data.get("scope"),
                                is_runtime=dep_data.get("is_runtime"),
                                is_optional=dep_data.get("is_optional"),
                                is_pinned=dep_data.get("is_pinned"),
                            )
                        elif isinstance(dep_data, DependentPackage):
                            dep = dep_data
                        else:
                            raise ValueError(
                                f"Cannot save object of type '{get_class_name(dep_data)}' to field '{field}' of type 'DependentPackage'"
                            )
                        unsaved_models.append(dep)

                if field == "parties":
                    for party_data in value:
                        if isinstance(party_data, dict | OrderedDict):
                            party = Party(
                                package=self,
                                type=party_data.get("type"),
                                role=party_data.get("role"),
                                name=party_data.get("name"),
                                email=party_data.get("email"),
                                url=party_data.get("url"),
                            )
                        elif isinstance(party_data, Party):
                            party = party_data
                        else:
                            raise ValueError(
                                f"Cannot save object of type '{get_class_name(party_data)}' to field '{field}' of type 'Party'"
                            )
                        unsaved_models.append(party)

                if field == "resources":
                    for resource_data in value:
                        if isinstance(resource_data, dict | OrderedDict):
                            resource = Resource(
                                package=self,
                                path=resource_data.get("path"),
                                is_file=resource_data.get("type") == "file",
                                name=resource_data.get("name"),
                                extension=resource_data.get("extension"),
                                size=resource_data.get("size"),
                                md5=resource_data.get("md5"),
                                sha1=resource_data.get("sha1"),
                                sha256=resource_data.get("sha256"),
                                mime_type=resource_data.get("mime_type"),
                                file_type=resource_data.get("file_type"),
                                programming_language=resource_data.get(
                                    "programming_language"
                                ),
                                is_binary=resource_data.get("is_binary"),
                                is_text=resource_data.get("is_text"),
                                is_archive=resource_data.get("is_archive"),
                                is_media=resource_data.get("is_media"),
                                is_key_file=resource_data.get("is_key_file"),
                            )
                            resource.set_scan_results(resource_data)
                        elif isinstance(resource_data, Resource):
                            resource = resource_data
                        else:
                            raise ValueError(
                                f"Cannot save object of type '{get_class_name(resource_data)}' to field '{field}' of type 'Resource'"
                            )
                        unsaved_models.append(resource)

                if unsaved_models:
                    created_models_count = len(unsaved_models)
                    model_count = 0
                    if field == "dependencies":
                        model_count = self.dependencies.all().count()
                        with transaction.atomic():
                            self.dependencies.all().delete()
                            DependentPackage.objects.bulk_create(unsaved_models)

                    if field == "parties":
                        model_count = self.parties.all().count()
                        with transaction.atomic():
                            self.parties.all().delete()
                            Party.objects.bulk_create(unsaved_models)

                    if field == "resources":
                        model_count = self.resources.all().count()
                        with transaction.atomic():
                            self.resources.all().delete()
                            Resource.objects.bulk_create(unsaved_models)

                    msg = f"Replaced {model_count} existing entries of field '{field}' with {created_models_count} new entries."
                    self.append_to_history(msg)
                    replaced_fields.extend([field, "history"])
            else:
                # Ensure the incoming value is of the correct type
                if field == "qualifiers" and isinstance(value, dict):
                    value = normalize_qualifiers(value, encode=True)

                date_fields = [
                    "created_date",
                    "last_indexed_date",
                    "last_modified_date",
                    "release_date",
                ]
                if field in date_fields and isinstance(value, str):
                    value = dateutil_parse(value)

                # Update field value
                package_value = getattr(self, field)
                setattr(self, field, value)

                # Cast datetime value to a string for history
                if field in date_fields:
                    package_value = str(package_value)
                    value = str(value)

                # Create entry for history
                entry = dict(
                    field=field,
                    old_value=package_value,
                    new_value=value,
                )
                history_entries.append(entry)
                updated_fields.append(field)

        if updated_fields and history_entries:
            data = {
                "updated_fields": history_entries,
            }
            self.append_to_history(
                "Package field values have been updated.",
                data=data,
                save=save,
            )
            updated_fields.append("history")

        if replaced_fields:
            updated_fields.extend(replaced_fields)

        if updated_fields:
            # Deduplicate field names
            updated_fields = list(set(updated_fields))

        return self, updated_fields


party_person = "person"
# often loosely defined
party_project = "project"
# more formally defined
party_org = "organization"
PARTY_TYPES = (
    (party_person, party_person),
    (party_project, party_project),
    (party_org, party_org),
)


class Party(models.Model):
    """A party is a person, project or organization related to a package."""

    package = models.ForeignKey(
        Package,
        related_name="parties",
        on_delete=models.CASCADE,
        help_text=_("The Package that this party is related to"),
    )

    type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=PARTY_TYPES,
        help_text=_("the type of this party"),
    )

    role = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_(
            "A role for this party. Something such as author, "
            "maintainer, contributor, owner, packager, distributor, "
            "vendor, developer, owner, etc."
        ),
    )

    name = models.CharField(
        max_length=255, blank=True, null=True, help_text=_("Name of this party.")
    )

    email = models.CharField(
        max_length=255, blank=True, null=True, help_text=_("Email for this party.")
    )

    url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("URL to a primary web page for this party."),
    )

    def to_dict(self):
        from packagedb.serializers import PartySerializer

        party_data = PartySerializer(self).data
        return party_data


class DependentPackage(models.Model):
    """An identifiable dependent package package object."""

    package = models.ForeignKey(
        Package,
        related_name="dependencies",
        on_delete=models.CASCADE,
        help_text=_("The Package that this dependent package is related to"),
    )

    purl = models.CharField(
        max_length=2048,
        blank=True,
        null=True,
        help_text=_("A compact purl package URL"),
    )

    extracted_requirement = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("A string defining version(s)requirements. Package-type specific."),
    )

    scope = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_(
            "The scope of this dependency, such as runtime, install, etc. "
            "This is package-type specific and is the original scope string."
        ),
    )

    is_runtime = models.BooleanField(
        default=True, help_text=_("True if this dependency is a runtime dependency.")
    )

    is_optional = models.BooleanField(
        default=False, help_text=_("True if this dependency is an optional dependency")
    )

    is_pinned = models.BooleanField(
        default=False,
        help_text=_(
            "True if this dependency version requirement has "
            "been resolved and this dependency url points to an "
            "exact version."
        ),
    )

    def to_dict(self):
        from packagedb.serializers import DependentPackageSerializer

        depedent_package_data = DependentPackageSerializer(self).data
        return depedent_package_data


class AbstractResource(models.Model):
    """These model fields should be kept in line with scancode.resource.Resource"""

    path = models.CharField(
        max_length=2000,
        help_text=_(
            "The full path value of a resource (file or directory) in the archive it is from."
        ),
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("File or directory name of this resource with its extension."),
    )

    extension = models.CharField(
        max_length=100,
        blank=True,
        help_text=_(
            "File extension for this resource (directories do not have an extension)."
        ),
    )

    size = models.BigIntegerField(
        blank=True,
        null=True,
        help_text=_("Size in bytes."),
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_(
            "MIME type (aka. media type) for this resource. "
            "See https://en.wikipedia.org/wiki/Media_type"
        ),
    )

    file_type = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("Descriptive file type for this resource."),
    )

    programming_language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Programming language of this resource if this is a code file."),
    )

    is_binary = models.BooleanField(default=False)
    is_text = models.BooleanField(default=False)
    is_archive = models.BooleanField(default=False)
    is_key_file = models.BooleanField(default=False)
    is_media = models.BooleanField(default=False)

    is_file = models.BooleanField(
        default=False,
        help_text=_("True if this Resource is a file, False if it is a Directory"),
    )

    @property
    def type(self):
        return "file" if self.is_file else "directory"

    @type.setter
    def type(self, value):
        if value == "file":
            self.is_file = True
        else:
            self.is_file = False

    def __str__(self):
        return self.path

    class Meta:
        abstract = True


class ScanFieldsModelMixin(models.Model):
    """
    Fields returned by the ScanCode-toolkit scans.

    This model is from ScanCode.io
    """

    detected_license_expression = models.TextField(
        blank=True,
        help_text=_("TODO"),
    )
    detected_license_expression_spdx = models.TextField(
        blank=True,
        help_text=_("TODO"),
    )
    license_detections = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of license detection details."),
    )
    license_clues = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of license clues."),
    )
    percentage_of_license_text = models.FloatField(
        blank=True,
        null=True,
        help_text=_("TODO"),
    )
    copyrights = models.JSONField(
        blank=True,
        default=list,
        help_text=_(
            "List of detected copyright statements (and related detection details)."
        ),
    )
    holders = models.JSONField(
        blank=True,
        default=list,
        help_text=_(
            "List of detected copyright holders (and related detection details)."
        ),
    )
    authors = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected authors (and related detection details)."),
    )
    package_data = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of Package data detected from this CodebaseResource"),
    )
    emails = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected emails (and related detection details)."),
    )
    urls = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected URLs (and related detection details)."),
    )

    class Meta:
        abstract = True

    @classmethod
    def scan_fields(cls):
        return [field.name for field in ScanFieldsModelMixin._meta.get_fields()]

    def set_scan_results(self, scan_results, save=False):
        """
        Set the values of the current instance's scan-related fields using
        `scan_results`. Return a list containing the names of the fields
        updated.
        """
        updated_fields = []
        scan_fields = self.scan_fields()
        for field_name, value in scan_results.items():
            if value and field_name in scan_fields:
                setattr(self, field_name, value)
                updated_fields.append(field_name)

        if save:
            self.save()

        return updated_fields

    def copy_scan_results(self, from_instance, save=False):
        """
        Copy the scan-related fields values from `from_instance`to the current
        instance.
        """
        for field_name in self.scan_fields():
            value_from_instance = getattr(from_instance, field_name)
            setattr(self, field_name, value_from_instance)

        if save:
            self.save()


class Resource(
    ExtraDataFieldMixin, HashFieldsMixin, ScanFieldsModelMixin, AbstractResource
):
    package = models.ForeignKey(
        Package,
        related_name="resources",
        on_delete=models.CASCADE,
        help_text=_("The Package that this Resource is from"),
    )

    git_sha1 = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text=_("git SHA1 checksum hex-encoded"),
    )

    class Meta:
        unique_together = (("package", "path"),)
        ordering = ("id",)
        indexes = [
            models.Index(fields=["md5"]),
            models.Index(fields=["sha1"]),
            models.Index(fields=["sha256"]),
            models.Index(fields=["sha512"]),
            models.Index(fields=["git_sha1"]),
        ]

    @property
    def for_packages(self):
        """Return the list of all Packages associated to this resource."""
        return [self.package.package_uid or str(self.package)]

    def to_dict(self):
        from packagedb.serializers import ResourceMetadataSerializer

        resource_metadata = ResourceMetadataSerializer(self).data
        return resource_metadata


class PackageRelation(models.Model):
    """
    A directed relationship between two packages.

    This consists of three attributes:
    - The "from" (or subject) package in the relationship,
    - the "to" (or object) package in the relationship,
    - and the "relationship" (or predicate) choice that specifies the relationship.
    """

    class Relationship(models.TextChoices):
        SOURCE_PACKAGE = "source_package"
        BINARY_PACKAGE = "binary_package"

    from_package = models.ForeignKey(
        Package,
        related_name="related_to",
        on_delete=models.CASCADE,
        editable=False,
    )

    to_package = models.ForeignKey(
        Package,
        related_name="related_from",
        on_delete=models.CASCADE,
        editable=False,
    )

    relationship = models.CharField(
        max_length=30,
        choices=Relationship.choices,
        help_text="Relationship between the from and to package "
        'URLs such as "source_package" when a package '
        "is the source code package for another package.",
    )

    def __str__(self):
        return (
            f"{self.from_package.purl} is the "
            f"{self.relationship.upper()} to {self.to_package.purl}"
        )


def make_relationship(
    from_package,
    to_package,
    relationship,
):
    """Create and return the from/to package relathionship if it does exists."""
    pkg, _created = PackageRelation.objects.get_or_create(
        from_package=from_package,
        to_package=to_package,
        relationship=relationship,
    )
    return pkg


class PackageWatch(models.Model):
    """Model representing a watch on a package to monitor for new versions."""

    DEPTH_CHOICES = (
        (1, "Version"),
        (2, "Metadata"),
        (3, "Scan"),
    )

    package_url = models.CharField(
        max_length=2048,
        unique=True,
        null=False,
        blank=False,
        db_index=True,
        help_text=_(
            "Package-URL to watch. If the PURL has a version, "
            "qualifiers or subpath, they are stripped and ignored."
        ),
    )

    type = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("A short code to identify the type of this package."),
    )

    namespace = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Package name prefix, such as Maven groupid, Docker image owner, "
            "GitHub user or organization, etc."
        ),
    )

    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Name of the package."),
    )

    is_active = models.BooleanField(
        null=True,
        db_index=True,
        default=True,
        help_text=_(
            "When set to True (Yes), this Package Watch is active. "
            "When set to False (No), this watch is inactive and not processed."
        ),
    )

    depth = models.PositiveSmallIntegerField(
        choices=DEPTH_CHOICES,
        default=3,
        help_text=_(
            "Depth of data collection from listing versions up to a full scan."
        ),
    )

    watch_interval = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message="Interval must be at least 1 day."),
            MaxValueValidator(365, message="Interval must be at most 365 days."),
        ],
        default=7,
        help_text=_("Number of days to wait between watches of this package."),
    )

    creation_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp indicating when this watch object was created."),
    )

    last_watch_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Timestamp indicating when this PURL was last watched."),
    )

    watch_error = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Watch error messages of the last watch, if any. "
            "When present this means the watch failed. "
            "This is reset on each new watch."
        ),
    )

    schedule_work_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Identifier used to manage the periodic watch job."),
    )

    def __str__(self):
        return f"{self.package_url}"

    def save(self, *args, **kwargs):
        schedule = False
        if not self.pk:
            try:
                purl = PackageURL.from_string(self.package_url)
            except ValueError as e:
                raise exceptions.ValidationError(
                    f"Error creating PackageWatch object: {e}"
                ) from e

            # we are removing version/qualifiers/subpath before saving
            self.package_url = str(
                PackageURL(
                    type=purl.type,
                    namespace=purl.namespace,
                    name=purl.name,
                )
            )
            self.type = purl.type
            self.name = purl.name
            self.namespace = purl.namespace

            # Schedule job for the newly created watch.
            schedule = True
        else:
            existing = PackageWatch.objects.get(pk=self.pk)
            if (
                existing.package_url != self.package_url
                or existing.name != self.name
                or existing.type != self.type
                or existing.namespace != self.namespace
            ):
                raise ValueError(
                    "The package_url, type, name, and namespace of a PackageWatch cannot be changed once saved."
                )
            # Update the scheduled job if watch_interval/is_active is modified.
            elif (
                existing.is_active != self.is_active
                or existing.watch_interval != self.watch_interval
            ):
                schedule = True

        if schedule:
            self.schedule_work_id = self.create_new_job()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Clear associated watch schedule."""
        if self.schedule_work_id and schedules.is_redis_running():
            schedules.clear_job(self.schedule_work_id)

        super().delete(*args, **kwargs)

    def create_new_job(self):
        """
        Create a new scheduled job. If a previous scheduled job
        exists remove the existing job from the scheduler.
        """
        if not schedules.is_redis_running():
            return
        if self.schedule_work_id:
            schedules.clear_job(self.schedule_work_id)

        return schedules.schedule_watch(self) if self.is_active else None


class PackageSet(models.Model):
    """A group of related Packages"""

    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        default=uuid.uuid4,
        unique=True,
        help_text=_("The identifier of the Package set"),
    )

    def add_to_package_set(self, package):
        self.packages.add(package)

    def get_package_set_members(self):
        """Return related Packages"""
        return self.packages.order_by(
            "package_content",
        )


class ApiUserManager(UserManager):
    def create_api_user(self, username, first_name="", last_name="", **extra_fields):
        """Create and return an API-only user. Raise ValidationError."""
        username = self.normalize_email(username)
        email = username
        self._validate_username(email)

        # note we use the email as username and we could instead override
        # django.contrib.auth.models.AbstractUser.USERNAME_FIELD

        user = self.create_user(
            username=email,
            email=email,
            password=None,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )

        # this ensure that this is not a valid password
        user.set_unusable_password()
        user.save()

        Token._default_manager.get_or_create(user=user)

        return user

    def _validate_username(self, email):
        """Validate username. If invalid, raise a ValidationError"""
        try:
            self.get_by_natural_key(email)
        except models.ObjectDoesNotExist:
            pass
        else:
            raise exceptions.ValidationError(
                f"Error: This email already exists: {email}"
            )


@receiver(models.signals.post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Create an API key token on user creation, using the signal system."""
    if created:
        Token.objects.get_or_create(user_id=instance.pk)


class PackageActivity(FederatedCodePackageActivityMixin):
    """Record of package activity from a FederatedCode."""

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("The identifier of the package activity"),
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp indicating when this object was created."),
    )

    is_processed = models.BooleanField(
        default=False, help_text=_("True if this activity has been processed.")
    )
