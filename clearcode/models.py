#
# Copyright (c) nexB Inc. and others. All rights reserved.
#
# ClearCode is a free software tool from nexB Inc. and others.
# Visit https://github.com/nexB/clearcode-toolkit/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gzip
import json
import uuid

from django.db import models


class VirtualFileStore:
    """Convenience wrapper to access CDitems as if they would be concrete files."""

    @classmethod
    def walk(self, prefix=None, since=None):
        """
        Yield tuples of (path, data, last modified) for CD items.
        Optionally return items that have a certain path prefix.
        Optionally return items that have have been modified `since` a datetime.
        """
        items = CDitem.objects.all()
        if prefix:
            items = items.filter(path__startswith=prefix)
        if since:
            items = items.filter(last_modified_date__ge=since)
        for item in items:
            yield item.path, item.data_content(), item.last_modified_date


class CDitemQuerySet(models.QuerySet):
    def known_package_types(self):
        # These are the Package types that can be stored in the PackageDB
        KNOWN_PACKAGE_TYPES = [
            "composer",
            "crate",
            "deb",
            "debsrc",
            "gem",
            "git",
            "maven",
            "npm",
            "nuget",
            "pypi",
            "sourcearchive",
        ]
        q_objs = models.Q()
        for package_type in KNOWN_PACKAGE_TYPES:
            q_objs.add(models.Q(path__startswith=package_type), models.Q.OR)
        return self.filter(q_objs)

    def definitions(self):
        return self.exclude(path__contains="/tool/")

    def scancode_harvests(self):
        return self.filter(path__contains="tool/scancode")

    def mappable(self):
        return self.filter(last_map_date__isnull=True, map_error__isnull=True)

    def mappable_definitions(self):
        return self.mappable().definitions().known_package_types()

    def mappable_scancode_harvests(self):
        return self.mappable().scancode_harvests().known_package_types()

    def modified_after(self, date):
        """Limit the QuerySet to CDitems that were modified after a given `date`."""
        return self.filter(last_modified_date__gt=date)


class CDitem(models.Model):
    """
    A simple key/value pair model where the key is the path to a JSON file as
    stored in ClearlyDefined blob storage and the value is a GZipped compressed
    JSON file content, stored as a binary bytes blob.
    """

    path = models.CharField(
        primary_key=True,
        max_length=2048,
        help_text="Path to the original file in the ClearlyDefined file storage.",
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    content = models.BinaryField(help_text="Actual gzipped JSON content.")

    last_modified_date = models.DateTimeField(
        help_text="Date and time that this record was last modified.",
        auto_now=True,  # Automatically set to now on object save()
    )

    last_map_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp set to the date of the last mapping. Used to track mapping status.",
    )

    map_error = models.TextField(
        null=True,
        blank=True,
        help_text="Mapping errors messages. When present this means the mapping failed.",
    )

    objects = CDitemQuerySet.as_manager()

    @property
    def data(self):
        """Return the data content deserialized from the content field."""
        uncompressed_content = gzip.decompress(self.content)
        if not uncompressed_content:
            uncompressed_content = "{}"
        return json.loads(uncompressed_content)
