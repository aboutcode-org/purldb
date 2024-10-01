#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json
from urllib.parse import urlsplit as _urlsplit

from django.shortcuts import render
from django.views import View
from django.views.generic.list import ListView

from packagedb import models
from packagedb.forms import PackageSearchForm

PAGE_SIZE = 20

print_to_console = False


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


class ValidatePurl(ListView):
    model = models.Package
    template_name = "validate_purl.html"
    ordering = ["type", "namespace", "name", "version", "qualifiers", "subpath"]
    paginate_by = PAGE_SIZE
    validation_errors = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_query = self.request.GET
        context["package_search_form"] = PackageSearchForm(request_query)
        context["search"] = request_query.get("search")

        if print_to_console:
            print(
                f"\nviews.py ValidatePurl() get_context_data context['search'] = {context['search']}"
            )

        context["packageurl_from_string"] = self.check_packageurl_from_string(
            request_query.get("search")
        )

        purl_components_tooltips = [
            {
                "text": "scheme",
                "attribute": "scheme",
                "tooltip_class": "tooltip-content",
                "required": True,
                "data_tooltip": "The scheme is a constant with the value 'pkg', and is followed by a ':' separator.",
            },
            {
                "text": "type",
                "attribute": "type",
                "tooltip_class": "tooltip-content",
                "required": True,
                "data_tooltip": "A short code to identify the type of this package. For example: gem for a Rubygem, docker for a container, pypi for a Python Wheel or Egg, maven for a Maven Jar, deb for a Debian package etc.",
            },
            {
                "text": "namespace",
                "attribute": "namespace",
                "tooltip_class": "tooltip-content",
                "required": False,
                "data_tooltip": "Package name prefix, such as Maven groupid, Docker image owner, GitHub user or organization, etc.",
            },
            {
                "text": "name",
                "attribute": "name",
                "tooltip_class": "tooltip-content",
                "required": True,
                "data_tooltip": "Name of the package.",
            },
            {
                "text": "version",
                "attribute": "version",
                "tooltip_class": "tooltip-content",
                "required": False,
                "data_tooltip": "Version of the package.",
            },
            {
                "text": "qualifiers",
                "attribute": "qualifiers",
                "tooltip_class": "tooltip-content",
                "required": False,
                "data_tooltip": "Extra qualifying data for a package, such as the name of an OS, architecture, distro, etc.",
            },
            {
                "text": "subpath",
                "attribute": "subpath",
                "tooltip_class": "tooltip-content",
                "required": False,
                "data_tooltip": "Extra subpath within a package, relative to the package root.",
            },
        ]
        context["purl_components_tooltips"] = purl_components_tooltips

        if self.validation_errors:
            context["validation_errors"] = self.validation_errors
        context["parse_purl_attributes"] = parse_purl(request_query.get("search"))
        if print_to_console:
            print(f"\ncontext = \n{context}\n")

        return context

    def get_queryset(self, query=None):
        query = query or self.request.GET.get("search") or ""
        if print_to_console:
            print(f"\nviews.py ValidatePurl() get_queryset query = {query}")
        result = self.model.objects.search(query)
        if isinstance(result, dict):  # If result is a validation error dictionary
            self.validation_errors = result  # Store errors in the instance attribute
            if print_to_console:
                print(f"\n==> result = {json.dumps(result, indent=4)}")
            return self.model.objects.none()  # Return an empty queryset

        return result.prefetch_related().order_by("version")

    def check_packageurl_from_string(self, query=None):
        query = query or self.request.GET.get("search") or ""
        if print_to_console:
            print(
                f"\nviews.py ValidatePurl check_packageurl_from_string() query = {query}"
            )
        result = self.model.objects.get_packageurl_from_string(query)

        return result


class ValidatedPurlDetails(ListView):
    model = models.Package
    template_name = "validated_purl_details.html"
    ordering = ["type", "namespace", "name", "version", "qualifiers", "subpath"]
    paginate_by = PAGE_SIZE
    validation_errors = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_query = self.request.GET
        context["package_search_form"] = PackageSearchForm(request_query)
        context["search"] = request_query.get("search")

        if self.validation_errors:
            context["validation_errors"] = self.validation_errors

        context["parse_purl_attributes"] = parse_purl(request_query.get("search"))

        purl_details_tooltips = [
            {
                "text": "Package URL",
                "attribute": "package_url",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "A Package URL (&quot;purl&quot;) is a URL string used to identify and locate a software package in a mostly universal and uniform way across programming languages, package managers, packaging conventions, tools, APIs and databases.",
            },
            {
                "text": "Filename",
                "attribute": "filename",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "The exact file name (typically an archive of some type) of the package. This is usually the name of the file as downloaded from a website.",
            },
            {
                "text": "Download URL",
                "attribute": "download_url",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "The download URL for obtaining the package.",
            },
            {
                "text": "Homepage URL",
                "attribute": "homepage_url",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "Homepage URL",
            },
            {
                "text": "Primary language",
                "attribute": "primary_language",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "The primary programming language associated with the package.",
            },
            {
                "text": "Description",
                "attribute": "description",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "Freeform description, preferably as provided by the author(s).",
            },
            {
                "text": "Type",
                "attribute": "type",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "A short code to identify the type of this package. For example: gem for a Rubygem, docker for a container, pypi for a Python Wheel or Egg, maven for a Maven Jar, deb for a Debian package, etc.",
            },
            {
                "text": "Name",
                "attribute": "name",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "Name of the package.",
            },
            {
                "text": "Version",
                "attribute": "version",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "Version of the package.",
            },
            {
                "text": "Release date",
                "attribute": "release_date",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "The date that the package file was created, or when it was posted to its original download source.",
            },
            {
                "text": "Declared license expression",
                "attribute": "declared_license_expression",
                "tooltip_class": "tooltip-content",
                "data_tooltip": "A license expression derived from statements in the manifest or key files of a software project, such as the NOTICE, COPYING, README and LICENSE files.",
            },
        ]
        context["purl_details_tooltips"] = purl_details_tooltips

        if print_to_console:
            print(f"\ncontext = {context}")

        return context

    def get_queryset(self, query=None):
        query = query or self.request.GET.get("search") or ""
        if print_to_console:
            print(f"\nValidatePurlDetails() get_queryset query = {query}")

        result = self.model.objects.search(query)
        if isinstance(result, dict):  # If result is a validation error dictionary
            self.validation_errors = result  # Store errors in the instance attribute
            print(
                f"\nValidatedPurlDetails.get_queryset() result = {json.dumps(result, indent=4)}"
            )
            return self.model.objects.none()  # Return an empty queryset

        return result.prefetch_related().order_by("version")


def parse_purl(query):
    if print_to_console:
        print(f"\nviews.py parse_purl() query = {query}")

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

    # ==> scheme component ===
    purl_pkg_scheme_component = "MISSING"
    if query:
        if not sep or scheme != "pkg":
            purl_error_message = (
                "The input purl is missing the required 'scheme' component."
            )
        else:
            purl_pkg_scheme_component = "pkg:"
            purl_error_message = "The input purl is valid."

    # ==> type component ===
    purl_type = "MISSING"
    # https://github.com/package-url/purl-spec/blob/version-range-spec/PURL-SPECIFICATION.rst#rules-for-each-purl-component:
    # purl parsers must accept URLs such as 'pkg://' and must ignore the '//'.
    remainder = remainder.strip().lstrip("/")
    type, sep, remainder = remainder.partition("/")  # NOQA
    if print_to_console:
        print(f"\ntype = {type}")
        print(f"sep = {sep}")
        print(f"remainder03 = {remainder}")

    if scheme == "pkg":
        if not type or not sep:
            purl_error_message = (
                "The input purl is missing the required 'type' component."
            )
        else:
            purl_type = type
    else:
        if not type or not sep:
            purl_error_message = (
                "The input purl is missing the required 'scheme' and 'type' components."
            )
        else:
            purl_type = type

    type = type.lower()

    # ==> user:pass@host:port code block ===
    scheme, authority, path, qualifiers_str, subpath = _urlsplit(
        url=remainder, scheme="", allow_fragments=True
    )

    if scheme or authority:
        msg = (
            f'\n\tInvalid purl {repr(query)} cannot contain a "user:pass@host:port" '
            f"\n\tURL Authority component: {repr(authority)}."
        )
        if print_to_console:
            print(f"ValueError = {ValueError(msg)}")

    # ==> namespace component ===
    namespace_01 = ""
    sep_01 = ""
    path_01 = ""
    path = path.lstrip("/")
    purl_namespace = ""
    namespace: str | None = ""
    # NPM purls have a namespace in the path and the namespace in an npm purl
    # is different from others because it starts with `@` so we need to handle
    # this case separately.
    if type == "npm" and path.startswith("@"):
        namespace, sep, path = path.partition("/")
    else:
        namespace_01, sep_01, path_01 = path.rpartition("/")
        namespace = namespace_01

    purl_namespace = namespace
    remainder, sep, version = path.rpartition("@")
    if not sep:
        remainder = version
        version = None

    purl_version = version

    # ==> name component ===
    purl_name = "MISSING"
    ns_name = remainder.strip().strip("/")
    ns_name_parts = ns_name.split("/")
    ns_name_parts = [seg for seg in ns_name_parts if seg and seg.strip()]
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

    if purl_pkg_scheme_component == "pkg:" and purl_type != "MISSING":
        if not name:
            purl_error_message = (
                "The input purl is missing the required 'name' component."
            )
        else:
            purl_name = name
    elif purl_pkg_scheme_component == "MISSING" and purl_type != "MISSING":
        if not name:
            purl_error_message = (
                "The input purl is missing the required 'scheme' and 'name' components."
            )
        else:
            purl_name = name
    elif purl_pkg_scheme_component == "MISSING" and purl_type == "MISSING":
        if not name:
            purl_error_message = "The input purl is missing the required 'scheme', 'type' and 'name' components."
        else:
            purl_name = name
    elif purl_pkg_scheme_component == "pkg:" and purl_type == "MISSING":
        if not name:
            purl_error_message = (
                "The input purl is missing the required 'type' and 'name' components."
            )
        else:
            purl_name = name

    # ==> qualifiers component ===
    purl_qualifiers = ""
    purl_qualifiers = qualifiers_str

    # ==> subpath component ===
    purl_subpath = ""
    purl_subpath = subpath

    parse_purl_attributes = {}
    parse_purl_attributes["input"] = query
    parse_purl_attributes["status"] = purl_error_message
    parse_purl_attributes["scheme"] = purl_pkg_scheme_component
    parse_purl_attributes["type"] = purl_type
    parse_purl_attributes["namespace"] = purl_namespace
    parse_purl_attributes["name"] = purl_name
    parse_purl_attributes["version"] = purl_version
    parse_purl_attributes["qualifiers"] = purl_qualifiers
    parse_purl_attributes["subpath"] = purl_subpath

    if print_to_console:
        print(f"\nparse_purl_attributes['input'] = {parse_purl_attributes['input']}")
        print(f"\nparse_purl_attributes['status'] = {parse_purl_attributes['status']}")
        print(f"\nparse_purl_attributes['scheme'] = {parse_purl_attributes['scheme']}")
        print(f"parse_purl_attributes['type'] = {parse_purl_attributes['type']}")
        print(
            f"parse_purl_attributes['namespace'] = {parse_purl_attributes['namespace']}"
        )
        print(f"parse_purl_attributes['name'] = {parse_purl_attributes['name']}")
        print(f"parse_purl_attributes['version'] = {parse_purl_attributes['version']}")
        print(
            f"parse_purl_attributes['qualifiers'] = {parse_purl_attributes['qualifiers']}"
        )
        print(f"parse_purl_attributes['subpath'] = {parse_purl_attributes['subpath']}")
        print("")

    return parse_purl_attributes
