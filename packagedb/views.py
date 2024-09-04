#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from urllib.parse import urlsplit as _urlsplit

from django.shortcuts import render
from django.views import View
from django.views.generic.list import ListView

from packagedb import models
from packagedb.forms import PackageSearchForm

PAGE_SIZE = 20


class HomePage(View):
    template_name = "index.html"

    def get(self, request):
        request_query = request.GET
        context = {
            "package_search_form": PackageSearchForm(request_query),
        }
        return render(
            request=request, template_name=self.template_name, context=context
        )


class PackageSearch(ListView):
    model = models.Package
    template_name = "packages.html"
    ordering = ["type", "namespace", "name", "version", "qualifiers", "subpath"]
    paginate_by = PAGE_SIZE
    validation_errors = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_query = self.request.GET
        context["package_search_form"] = PackageSearchForm(request_query)
        context["search"] = request_query.get("search")

        if self.validation_errors:
            context["validation_errors"] = (
                self.validation_errors
            )  # Pass the errors to the context
        context["purl_attributes"] = self.parse_purl(request_query.get("search"))
        return context

    def get_queryset(self, query=None):
        query = query or self.request.GET.get("search") or ""
        result = self.model.objects.search(query)

        if isinstance(result, dict):  # If result is a validation error dictionary
            self.validation_errors = result  # Store errors in the instance attribute
            return self.model.objects.none()  # Return an empty queryset
        return result.prefetch_related().order_by("version")

    def parse_purl(self, query):
        purl_error_message = "PURL parsing under development."
        purl_pkg_scheme_component = "AAA"
        purl_type = "BBB"
        purl_namespace = "CCC"
        purl_name = "DDD"
        purl_version = "EEE"
        purl_qualifiers = "FFF"
        purl_subpath = "GGG"

        purl_attributes = {}
        purl_attributes["input"] = query
        purl_attributes["status"] = purl_error_message
        purl_attributes["scheme"] = purl_pkg_scheme_component
        purl_attributes["type"] = purl_type
        purl_attributes["namespace"] = purl_namespace
        purl_attributes["name"] = purl_name
        purl_attributes["version"] = purl_version
        purl_attributes["qualifiers"] = purl_qualifiers
        purl_attributes["subpath"] = purl_subpath

        return purl_attributes


# NOTE Test a tabset alternative.  Update: per feedback, no tabset, but keep this class' parse_purl() method for the next iteration incorporating the Thur. tech talk feedback.
class PackageSearchTestTabset(ListView):
    model = models.Package
    template_name = "test_tabset.html"
    ordering = ["type", "namespace", "name", "version", "qualifiers", "subpath"]
    paginate_by = PAGE_SIZE
    validation_errors = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_query = self.request.GET
        context["package_search_form"] = PackageSearchForm(request_query)
        context["search"] = request_query.get("search")

        # Tooltips for each input purl component.
        tooltip_default = (
            "has-tooltip-multiline has-tooltip-black has-tooltip-arrow tooltip-narrow"
        )
        tooltip_error = "has-text-danger has-tooltip-multiline has-tooltip-danger has-tooltip-arrow tooltip-wide-error"
        purl_tooltips = [
            {
                "text": "pkg:",
                "tooltip_class": tooltip_default,
                "data_tooltip": "scheme",
            },
            {"text": "maven", "tooltip_class": tooltip_default, "data_tooltip": "type"},
            {"text": "/"},
            {
                "text": "org.elasticsearch",
                "tooltip_class": tooltip_error,
                "data_tooltip": "namespace",
            },
            {"text": "/"},
            {
                "text": "elasticsearch",
                "tooltip_class": tooltip_default,
                "data_tooltip": "name",
            },
            {"text": "@"},
            {
                "text": "7.17.9",
                "tooltip_class": tooltip_default,
                "data_tooltip": "version",
            },
            {"text": "?"},
            {
                "text": "classifier=sources",
                "tooltip_class": tooltip_default,
                "data_tooltip": "qualifiers",
            },
        ]
        context["purl_tooltips"] = purl_tooltips

        if self.validation_errors:
            context["validation_errors"] = (
                self.validation_errors
            )  # Pass the errors to the context
        context["purl_attributes"] = self.parse_purl(request_query.get("search"))
        return context

    def get_queryset(self, query=None):
        query = query or self.request.GET.get("search") or ""
        result = self.model.objects.search(query)
        if isinstance(result, dict):  # If result is a validation error dictionary
            self.validation_errors = result  # Store errors in the instance attribute
            return self.model.objects.none()  # Return an empty queryset

        return result.prefetch_related().order_by("version")

    def parse_purl(self, query):
        # purl_error_message = "The input purl is valid."
        purl_error_message = ""
        purl_pkg_scheme_component = "AAA"
        purl_type = "BBB"
        purl_namespace = "CCC"
        purl_name = "DDD"
        purl_version = "EEE"
        purl_qualifiers = "FFF"
        purl_subpath = "GGG"

        if not query:
            return

        scheme, sep, remainder = query.partition(":")
        # print(f"scheme = {scheme}")
        # print(f"sep = {sep}")
        # print(f"remainder01 = {remainder}")

        # ==> scheme component ===
        purl_pkg_scheme_component = "MISSING"

        if query:
            if not sep or scheme != "pkg":
                purl_error_message = (
                    "The input purl is missing the required 'scheme' component."
                )
            else:
                purl_pkg_scheme_component = "pkg:"
                # TODO 2024-09-03 Tuesday 14:03:59.  Add this here after redefining default as ""?
                purl_error_message = "The input purl is valid."

        # print(f"\npurl_error_message_pkg = {purl_error_message}")

        # ==> type component ===
        purl_type = "MISSING"

        # From original code:
        # this strip '/, // and /// as possible in :// or :///
        # TODO 2024-09-03 Tuesday 15:08:12.  Why do we do this for just 1 leading '/'?
        # remainder = remainder.strip().lstrip("/")
        # Try this instead w/o left stripping and vet results.

        # print(f"\nremainder02 = {remainder}")

        type, sep, remainder = remainder.partition("/")  # NOQA
        # print(f"\ntype = {type}")
        # print(f"sep = {sep}")
        # print(f"remainder03 = {remainder}")

        if scheme == "pkg":
            if not type or not sep:
                purl_error_message = (
                    "The input purl is missing the required 'type' component."
                )
            else:
                purl_type = type
        else:
            if not type or not sep:
                purl_error_message = "The input purl is missing the required 'scheme' and 'type' components."
            else:
                purl_type = type
        # print(f"\npurl_error_message_type = {purl_error_message}")

        type = type.lower()

        # ==> user:pass@host:port code block ===
        # TODO ==> REMEMBER TO COME BACK TO THIS:
        # Note that 'path' is defined just below and if not the following 'path' definition fails -- UnboundLocalError: local variable 'path' referenced before assignment

        scheme, authority, path, qualifiers_str, subpath = _urlsplit(
            url=remainder, scheme="", allow_fragments=True
        )
        # print(f"\n==> after _urlsplit:")
        # print(f"==> scheme = {scheme}")
        # print(f"==> authority = {authority}")
        # print(f"==> path = {path}")
        # print(f"==> qualifiers_str = {qualifiers_str}")
        # print(f"==> subpath = {subpath}")

        # if scheme or authority:
        #     msg = (
        #         f'Invalid purl {repr(purl)} cannot contain a "user:pass@host:port" '
        #         f"URL Authority component: {repr(authority)}."
        #     )
        #     raise ValueError(msg)

        # ==> namespace component ===
        # TEST Temp test definitions
        namespace_01 = ""
        sep_01 = ""
        path_01 = ""

        # print(f"\n==> path before [path = path.lstrip('/')] = {path}")

        path = path.lstrip("/")

        # 2024-08-28 Wednesday 15:12:56.
        # print(f"==> starting path for namespace and version = {path}")

        purl_namespace = ""
        # From original code:
        namespace: str | None = ""
        # NPM purl have a namespace in the path
        # and the namespace in an npm purl is
        # different from others because it starts with `@`
        # so we need to handle this case separately
        if type == "npm" and path.startswith("@"):
            namespace, sep, path = path.partition("/")
            # print(f"\nnamespace = {namespace}")
            # print(f"sep = {sep}")
            # print(f"path = {path}")

        # TEST 2024-08-28 Wednesday 15:58:54.  Can we grab the namespace when it's not npm/@mynamespace?
        else:
            # namespace_01, sep_01, path_01 = path.partition("/")

            # path_01 = path.partition("/")
            # path_01 = path.rpartition("/")
            namespace_01, sep_01, path_01 = path.rpartition("/")

            # 2024-08-28 Wednesday 16:56:27.  Try this:
            namespace = namespace_01

        # print(f"==> namespace = {namespace}")
        # print(f"==> sep = {sep}")
        # print(f"==> path = {path}")
        # print("---")
        # print(f"==> namespace_01 = {namespace_01}")
        # print(f"==> sep_01 = {sep_01}")
        # print(f"==> path_01 = {path_01}")

        purl_namespace = namespace
        # print("=======")

        remainder, sep, version = path.rpartition("@")
        # print(f"\nremainder = {remainder}")
        # print(f"sep = {sep}")
        # print(f"version = {version}")
        if not sep:
            remainder = version
            version = None

        # TODO Define version here?
        purl_version = version

        # print(f"==> remainder04 = {remainder}")
        # print(f"==> sep = {sep}")
        # print(f"==> version = {version}")

        # ==> name component ===
        purl_name = "MISSING"

        ns_name = remainder.strip().strip("/")
        ns_name_parts = ns_name.split("/")
        ns_name_parts = [seg for seg in ns_name_parts if seg and seg.strip()]
        # print(f"\n==> ns_name = {ns_name}")
        # print(f"\n==> ns_name_parts = {ns_name_parts}")
        name = ""

        if not namespace and len(ns_name_parts) > 1:
            name = ns_name_parts[-1]
            ns = ns_name_parts[0:-1]
            namespace = "/".join(ns)
        elif namespace and len(ns_name_parts) > 1:
            name = ns_name_parts[-1]
        # This is in the original code:
        elif len(ns_name_parts) == 1:
            name = ns_name_parts[0]

        # print(f"\nname = {name}")

        if purl_pkg_scheme_component == "pkg:" and purl_type != "MISSING":
            if not name:
                purl_error_message = (
                    "The input purl is missing the required 'name' component."
                )
            else:
                purl_name = name
        elif purl_pkg_scheme_component == "MISSING" and purl_type != "MISSING":
            if not name:
                purl_error_message = "The input purl is missing the required 'scheme' and 'name' components."
            else:
                purl_name = name
        elif purl_pkg_scheme_component == "MISSING" and purl_type == "MISSING":
            if not name:
                purl_error_message = "The input purl is missing the required 'scheme', 'type' and 'name' components."
            else:
                purl_name = name
        elif purl_pkg_scheme_component == "pkg:" and purl_type == "MISSING":
            if not name:
                purl_error_message = "The input purl is missing the required 'type' and 'name' components."
            else:
                purl_name = name

        # ==> qualifiers component ===
        purl_qualifiers = ""
        # temp
        purl_qualifiers = qualifiers_str

        # to come

        # ==> subpath component ===
        purl_subpath = ""
        # temp
        purl_subpath = subpath

        # to come

        # print(f"\n1. -- scheme = {scheme}")
        # print(f"1A. -- purl_pkg_scheme_component = {purl_pkg_scheme_component}")
        # print(f"2. -- type = {type}")
        # print(f"2A. -- purl_type = {purl_type}")
        # print(f"3. -- namespace = {namespace}")
        # print(f"3A. -- purl_namespace = {purl_namespace}")
        # print(f"4. -- name = {name}")
        # print(f"4A. -- purl_name = {purl_name}")
        # # purl_qualifiers
        # # purl_subpath

        # print(f"\npurl_error_message_name = {purl_error_message}")

        # ===================================================================

        purl_attributes = {}
        purl_attributes["input"] = query
        purl_attributes["status"] = purl_error_message
        purl_attributes["scheme"] = purl_pkg_scheme_component
        purl_attributes["type"] = purl_type
        purl_attributes["namespace"] = purl_namespace
        purl_attributes["name"] = purl_name
        purl_attributes["version"] = purl_version
        purl_attributes["qualifiers"] = purl_qualifiers
        purl_attributes["subpath"] = purl_subpath

        print(f"\npurl_attributes['input'] = {purl_attributes['input']}")
        print(f"purl_attributes['status'] = {purl_attributes['status']}")
        print(f"purl_attributes['scheme'] = {purl_attributes['scheme']}")
        print(f"purl_attributes['type'] = {purl_attributes['type']}")
        print(f"purl_attributes['namespace'] = {purl_attributes['namespace']}")
        print(f"purl_attributes['name'] = {purl_attributes['name']}")
        print(f"purl_attributes['version'] = {purl_attributes['version']}")
        print(f"purl_attributes['qualifiers'] = {purl_attributes['qualifiers']}")
        print(f"purl_attributes['subpath'] = {purl_attributes['subpath']}")
        print("")

        return purl_attributes
