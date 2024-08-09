#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import shlex

import django_filters
from django.core.exceptions import FieldError
from django.db.models import Q

# The function and Classes in this file are from https://github.com/aboutcode-org/scancode.io/blob/main/scanpipe/filters.py


def parse_query_string_to_lookups(query_string, default_lookup_expr, default_field):
    """Parse a query string and convert it into queryset lookups using Q objects."""
    lookups = Q()
    terms = shlex.split(query_string)

    lookup_types = {
        "=": "iexact",
        "^": "istartswith",
        "$": "iendswith",
        "~": "icontains",
        ">": "gt",
        "<": "lt",
    }

    for term in terms:
        lookup_expr = default_lookup_expr
        negated = False

        if ":" in term:
            field_name, search_value = term.split(":", maxsplit=1)
            if field_name.endswith(tuple(lookup_types.keys())):
                lookup_symbol = field_name[-1]
                lookup_expr = lookup_types.get(lookup_symbol)
                field_name = field_name[:-1]

            if field_name.startswith("-"):
                field_name = field_name[1:]
                negated = True

        else:
            search_value = term
            field_name = default_field

        lookups &= Q(
            **{f"{field_name}__{lookup_expr}": search_value}, _negated=negated)

    return lookups


class QuerySearchFilter(django_filters.CharFilter):
    """Add support for complex query syntax in search filter."""

    def filter(self, qs, value):
        if not value:
            return qs

        lookups = parse_query_string_to_lookups(
            query_string=value,
            default_lookup_expr=self.lookup_expr,
            default_field=self.field_name,
        )

        try:
            return qs.filter(lookups)
        except FieldError:
            return qs.none()


class PackageSearchFilter(QuerySearchFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        if value.startswith("pkg:"):
            return qs.for_package_url(value)

        if "://" not in value and ":" in value:
            return super().filter(qs, value)

        search_fields = ["type", "namespace",
                         "name", "version", "download_url"]
        lookups = Q()
        for field_names in search_fields:
            lookups |= Q(**{f"{field_names}__{self.lookup_expr}": value})

        return qs.filter(lookups)
