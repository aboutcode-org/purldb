#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.db.models import Q

from matchcode.utils import MatchcodeTestCase
from matchcode.utils import build_purl_filter


class BuildPurlFilterTestCase(MatchcodeTestCase):
    def test_build_purl_filter_single_purl_no_prefix(self):
        purls = ["pkg:maven/commons-io/commons-io@2.11.0"]
        result = build_purl_filter(purls)

        expected = Q(
            type="maven",
            namespace="commons-io",
            name="commons-io",
            version="2.11.0",
            qualifiers="",
            subpath="",
        )
        self.assertEqual(expected, result)

    def test_build_purl_filter_single_purl_with_prefix(self):
        purls = ["pkg:maven/commons-io/commons-io@2.11.0"]
        result = build_purl_filter(purls, relation_prefix="package__")

        expected = Q(
            package__type="maven",
            package__namespace="commons-io",
            package__name="commons-io",
            package__version="2.11.0",
            package__qualifiers="",
            package__subpath="",
        )
        self.assertEqual(expected, result)

    def test_build_purl_filter_multiple_purls(self):
        purls = [
            "pkg:maven/commons-io/commons-io@2.11.0",
            "pkg:npm/lodash@4.17.21",
        ]
        result = build_purl_filter(purls)

        expected = Q(
            type="maven",
            namespace="commons-io",
            name="commons-io",
            version="2.11.0",
            qualifiers="",
            subpath="",
        ) | Q(
            type="npm",
            namespace="",
            name="lodash",
            version="4.17.21",
            qualifiers="",
            subpath="",
        )
        self.assertEqual(expected, result)
        self.assertEqual(Q.OR, result.connector)

    def test_build_purl_filter_with_qualifiers(self):
        purls = ["pkg:maven/commons-io/commons-io@2.11.0?classifier=sources"]
        result = build_purl_filter(purls)

        expected = Q(
            type="maven",
            namespace="commons-io",
            name="commons-io",
            version="2.11.0",
            qualifiers="classifier=sources",
            subpath="",
        )
        self.assertEqual(expected, result)

    def test_build_purl_filter_empty_list_returns_empty_q(self):
        result = build_purl_filter([])
        self.assertEqual(Q(), result)
