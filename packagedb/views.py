#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packagedb.models import Package

from django.views.generic import ListView
from django.views.generic.detail import DetailView

PAGE_SIZE = 20

class TableColumnsMixin:
    """
    table_columns = [
        "<field_name>",
        "<field_name>",
        {
            "field_name": "<field_name>",
            "label": None,
            "condition": None,
            "sort_name": None,
            "css_class": None,
        },
    ]
    """

    table_columns = []

    def get_columns_data(self):
        """Return the columns data structure used in template rendering."""
        columns_data = []

        sortable_fields = []
        active_sort = ""
        filterset = getattr(self, "filterset", None)
        if filterset and "sort" in filterset.filters:
            sortable_fields = list(filterset.filters["sort"].param_map.keys())
            active_sort = filterset.data.get("sort", "")

        for column_definition in self.table_columns:
            # Support for single "field_name" entry in columns list.
            if not isinstance(column_definition, dict):
                field_name = column_definition
                column_data = {"field_name": field_name}
            else:
                field_name = column_definition.get("field_name")
                column_data = column_definition.copy()

            condition = column_data.get("condition", None)
            if condition is not None and not bool(condition):
                continue

            if "label" not in column_data:
                column_data["label"] = self.get_field_label(field_name)

            sort_name = column_data.get("sort_name") or field_name
            if sort_name in sortable_fields:
                is_sorted = sort_name == active_sort.lstrip("-")

                sort_direction = ""
                if is_sorted and not active_sort.startswith("-"):
                    sort_direction = "-"

                column_data["is_sorted"] = is_sorted
                column_data["sort_direction"] = sort_direction
                query_dict = self.request.GET.copy()
                query_dict["sort"] = f"{sort_direction}{sort_name}"
                column_data["sort_query"] = query_dict.urlencode()

            if filter_fieldname := column_data.get("filter_fieldname"):
                column_data["filter"] = filterset.form[filter_fieldname]

            columns_data.append(column_data)

        return columns_data

    @staticmethod
    def get_field_label(field_name):
        """Return a formatted label for display based on the `field_name`."""
        return field_name.replace("_", " ").capitalize().replace("url", "URL")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns_data"] = self.get_columns_data()
        context["request_query_string"] = self.request.GET.urlencode()
        return context

class PackageListView(
    TableColumnsMixin,
    ListView
):
    model = Package
    paginate_by = PAGE_SIZE
    template_name = "package/package_list.html"
    table_columns = [
        {
            "field_name": "package_url",
            "label": "Purl",
            "sort_name": "projectmessages_count",
        },
        "name",
        "type",
        {
            "field_name": "other_license_expression_spdx",
            "label": "License",
        },
        {
            "field_name": "download_url",
            "label": "Download Url",
        },
        {
            "field_name": "created_date",
            "label": "Created Date",
            "sort_name": "created_date",
        }
    ]

class PackageDetailView(DetailView):
    model = Package
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "package/package_detail.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("parties", "dependencies")
        )
