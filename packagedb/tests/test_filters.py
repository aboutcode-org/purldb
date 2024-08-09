#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.test import TestCase
from packagedb.api import PackageFilterSet
from packagedb.filters import parse_query_string_to_lookups
from packagedb.models import Package


class PackageDBFilterTest(TestCase):

    def test_scanpipe_filters_package_filterset_search(self):
        p1 = Package.objects.create(
            type='maven',
            namespace='org.example',
            name='foo',
            version='1.0.0',
            download_url='https://example.com/foo-1.0.0.jar',
        )
        p2 = Package.objects.create(
            type='maven',
            namespace='org.somethingelse',
            name='foo',
            version='0.35.7',
            download_url='https://somethingelse.net/foo-0.35.7.jar',
        )

        filterset = PackageFilterSet(data={})
        self.assertEqual(2, len(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.purl})
        self.assertEqual([p1], list(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.version})
        self.assertEqual([p1], list(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.name})
        self.assertEqual(2, len(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.type})
        self.assertEqual(2, len(filterset.qs))

    def test_packagedb_filters_parse_query_string_to_lookups(self):
        inputs = {
            "LICENSE": "(AND: ('name__icontains', 'LICENSE'))",
            "two words": (
                "(AND: ('name__icontains', 'two'), ('name__icontains', 'words'))"
            ),
            "'two words'": "(AND: ('name__icontains', 'two words'))",
            "na me:LICENSE": (
                "(AND: ('name__icontains', 'na'), ('me__icontains', 'LICENSE'))"
            ),
            "name:LICENSE": "(AND: ('name__icontains', 'LICENSE'))",
            "default_value name:LICENSE": (
                "(AND: ('name__icontains', 'default_value'), "
                "('name__icontains', 'LICENSE'))"
            ),
            'name:"name with spaces"': "(AND: ('name__icontains', 'name with spaces'))",
            "name:'name with spaces'": "(AND: ('name__icontains', 'name with spaces'))",
            "-name:LICENSE -name:NOTICE": (
                "(AND: (NOT (AND: ('name__icontains', 'LICENSE'))), "
                "(NOT (AND: ('name__icontains', 'NOTICE'))))"
            ),
            "name:LICENSE status:scanned": (
                "(AND: ('name__icontains', 'LICENSE'), "
                "('status__icontains', 'scanned'))"
            ),
            'name^:"file"': "(AND: ('name__istartswith', 'file'))",
            'name$:".zip"': "(AND: ('name__iendswith', '.zip'))",
            'name=:"LICENSE"': "(AND: ('name__iexact', 'LICENSE'))",
            'name~:"LIC"': "(AND: ('name__icontains', 'LIC'))",
            'count<:"100"': "(AND: ('count__lt', '100'))",
            'count>:"10"': "(AND: ('count__gt', '10'))",
        }

        for query_string, expected in inputs.items():
            lookups = parse_query_string_to_lookups(query_string, "icontains", "name")
            self.assertEqual(expected, str(lookups))
