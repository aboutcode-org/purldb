#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import version
from itertools import groupby
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS, versions
from packageurl import PackageURL
from packageurl.contrib import purl2url

LOG_FILE_LOCATION = os.path.join(os.path.expanduser("~"), "purlcli.log")


@click.group()
def purlcli():
    """
    Return information for a PURL or list of PURLs.
    """


@purlcli.command(name="metadata")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    metavar="PURL",
    required=True,
    help="Package-URL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    metavar="FILE",
    required=False,
    default="-",
    show_default=True,
    help="Write output as JSON to FILE. Default is to print on screen.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    metavar="FILE",
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
@click.option(
    "--unique",
    is_flag=True,
    required=False,
    help="Return data only for unique PURLs.",
)
def get_metadata(purls, output, file, unique):
    """
    Fetch package metadata for a PURL.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    metadata_info = get_metadata_details(purls, output, file, unique, command_name)
    json.dump(metadata_info, output, indent=4)


def get_metadata_details(purls, output, file, unique, command_name):
    """
    Return a dictionary containing metadata for each PURL in the `purls` input
    list.  `check_metadata_purl()` will print an error message to the console
    (also displayed in the JSON output) when necessary.
    """
    metadata_details = {}
    metadata_details["headers"] = []
    metadata_details["packages"] = []

    metadata_warnings = {}

    input_purls, normalized_purls = normalize_purls(purls, unique)

    clear_log_file()

    for purl in input_purls:
        purl = purl.strip()
        if not purl:
            continue

        purl_data = {}
        purl_data["purl"] = purl

        metadata_purl = check_metadata_purl(purl)

        if command_name == "metadata" and metadata_purl:
            metadata_warnings[purl] = metadata_purl
            continue

        metadata_collection = collect_metadata(purl)
        purl_data["metadata"] = metadata_collection
        metadata_details["packages"].append(purl_data)

    metadata_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        command_name=command_name,
        normalized_purls=normalized_purls,
        unique=unique,
        purl_warnings=metadata_warnings,
    )

    return metadata_details


def collect_metadata(purl):
    """
    Return a list of release-based metadata collections from fetchcode/package.py.
    """
    collected_metadata = []
    for release in list(info(purl)):
        release_detail = release.to_dict()
        release_detail.move_to_end("purl", last=False)
        collected_metadata.append(release_detail)

    return collected_metadata


def check_metadata_purl(purl):
    """
    Return a variable identifying the message for printing to the console by
    get_metadata_details() if (1) the input PURL is invalid, (2) its type is not
    supported by `metadata` or (3) its existence was not validated (e.g.,
    "does not exist in the upstream repo").

    This message will also be reported by construct_headers() in the
    `warnings` field of the `header` section of the JSON object returned by
    the `metadata` command.
    """
    check_validation = validate_purl(purl)
    if check_validation is None:
        return "validation_error"
    results = check_validation

    if results["valid"] == False:
        return "not_valid"

    # This is manually constructed from a visual inspection of fetchcode/package.py.
    metadata_supported_ecosystems = [
        "bitbucket",
        "cargo",
        "github",
        "npm",
        "pypi",
        "rubygems",
    ]
    metadata_purl = PackageURL.from_string(purl)

    if metadata_purl.type not in metadata_supported_ecosystems:
        return "valid_but_not_supported"

    if results["exists"] == False:
        return "not_in_upstream_repo"

    if results["exists"] == None:
        return "check_existence_not_supported"


def normalize_purls(purls, unique):
    """
    If the command includes the `--unique` flag, take the list of input PURLs,
    remove the portion of the PURL that starts with a PURL separator (`@`, `?`
    or `#`), and return a deduplicated list of the resulting PURLs (in
    `input_purls`) and a list of tuples of each pair of the original input PURL
    and the normalized PURL (in `normalized_purls`).
    """
    input_purls = []
    normalized_purls = []
    if unique:
        for purl in purls:
            input_purl = purl
            purl = purl.strip()
            purl = re.split("[@,?,#,]+", purl)[0]
            normalized_purl = purl
            normalized_purls.append((input_purl, normalized_purl))
            if normalized_purl not in input_purls:
                input_purls.append(normalized_purl)
    else:
        input_purls = purls

    return input_purls, normalized_purls


def construct_headers(
    purls=None,
    output=None,
    file=None,
    command_name=None,
    head=None,
    normalized_purls=None,
    unique=None,
    purl_warnings=None,
):
    """
    Return a list comprising the `headers` content of the dictionary output.
    """
    headers = []
    headers_content = {}
    options = {}
    errors = []
    warnings = []

    context_purls = [p for p in purls]
    context_file = file
    context_file_name = None
    if context_file:
        context_file_name = context_file.name

    headers_content["tool_name"] = "purlcli"
    headers_content["tool_version"] = version("purldb_toolkit")

    options["command"] = command_name
    options["--purl"] = context_purls
    options["--file"] = context_file_name

    if head:
        options["--head"] = True

    if unique:
        options["--unique"] = True

    if isinstance(output, str):
        options["--output"] = output
    else:
        options["--output"] = output.name

    headers_content["options"] = options
    headers_content["purls"] = purls

    if (command_name in ["metadata", "urls", "validate", "versions"]) and unique:
        for input_purl, normalized_purl in normalized_purls:
            if input_purl != normalized_purl:
                warnings.append(
                    f"input PURL: '{input_purl}' normalized to '{normalized_purl}'"
                )

    for purl in purls:
        if not purl:
            continue

        warning_text = {
            "error_fetching_purl": f"'error fetching {purl}'",
            "validation_error": f"'{purl}' encountered a validation error",
            "not_valid": f"'{purl}' not valid",
            "valid_but_not_supported": f"'{purl}' not supported with `{command_name}` command",
            "valid_but_not_fully_supported": f"'{purl}' not fully supported with `urls` command",
            "not_in_upstream_repo": f"'{purl}' does not exist in the upstream repo",
            "check_existence_not_supported": f"'check_existence' is not supported for '{purl}'",
        }

        if command_name in ["metadata", "urls", "validate", "versions"]:
            purl_warning = purl_warnings.get(purl, None)

            if purl_warning:
                warning = warning_text[purl_warning]
                warnings.append(warning)
                continue

    log_file = Path(LOG_FILE_LOCATION)
    if log_file.is_file():
        with open(log_file, "r") as f:
            for line in f:
                errors.append(line)

    headers_content["errors"] = errors
    headers_content["warnings"] = warnings
    headers.append(headers_content)

    return headers


@purlcli.command(name="urls")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    metavar="PURL",
    help="Package-URL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    metavar="FILE",
    required=False,
    default="-",
    show_default=True,
    help="Write output as JSON to FILE. Default is to print on screen.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    metavar="FILE",
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
@click.option(
    "--unique",
    is_flag=True,
    required=False,
    help="Return data only for unique PURLs.",
)
@click.option(
    "--head",
    is_flag=True,
    required=False,
    help="Validate each URL's existence with a head request.",
)
def get_urls(purls, output, file, unique, head):
    """
    Return known URLs for a PURL.

    This includes the "download_url" which is the standard download URL, the "repo_download_url"
    which is the download URL provided by the package repository, the "repo_url" which is the URL of
    this package on the package repository.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    urls_info = get_urls_details(purls, output, file, unique, head, command_name)
    json.dump(urls_info, output, indent=4)


def get_urls_details(purls, output, file, unique, head, command_name):
    """
    Return a dictionary containing URLs for each PURL in the `purls` input
    list.  `check_urls_purl()` will print an error message to the console
    (also displayed in the JSON output) when necessary.
    """
    urls_details = {}
    urls_details["headers"] = []
    urls_details["packages"] = []

    urls_warnings = {}

    input_purls, normalized_purls = normalize_purls(purls, unique)

    clear_log_file()

    for purl in input_purls:
        url_detail = {}
        url_detail["purl"] = purl

        purl = purl.strip()
        if not purl:
            continue

        purl_status = check_urls_purl(purl)

        if command_name == "urls" and purl_status in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
        ]:
            urls_warnings[purl] = purl_status
            continue

        if command_name == "urls" and purl_status in ["valid_but_not_fully_supported"]:
            urls_warnings[purl] = purl_status

        # Add the URLs.
        url_purl = PackageURL.from_string(purl)

        url_detail["download_url"] = {"url": purl2url.get_download_url(purl)}

        url_detail["inferred_urls"] = [
            {"url": inferred} for inferred in purl2url.get_inferred_urls(purl)
        ]

        url_detail["repo_download_url"] = {"url": purl2url.get_repo_download_url(purl)}

        url_detail["repo_download_url_by_package_type"] = {
            "url": purl2url.get_repo_download_url_by_package_type(
                url_purl.type, url_purl.namespace, url_purl.name, url_purl.version
            )
        }

        url_detail["repo_url"] = {"url": purl2url.get_repo_url(purl)}

        url_detail["url"] = {"url": purl2url.get_url(purl)}

        # Add the http status code data.
        url_list = [
            "download_url",
            # "inferred_urls" has to be handled separately because it has a nested list
            "repo_download_url",
            "repo_download_url_by_package_type",
            "repo_url",
            "url",
        ]
        if head:
            for purlcli_url in url_list:
                url_detail[purlcli_url]["get_request_status_code"] = make_head_request(
                    url_detail[purlcli_url]["url"]
                ).get("get_request")
                url_detail[purlcli_url]["head_request_status_code"] = make_head_request(
                    url_detail[purlcli_url]["url"]
                ).get("head_request")

            for inferred_url in url_detail["inferred_urls"]:
                inferred_url["get_request_status_code"] = make_head_request(
                    inferred_url["url"]
                ).get("get_request")
                inferred_url["head_request_status_code"] = make_head_request(
                    inferred_url["url"]
                ).get("head_request")

        urls_details["packages"].append(url_detail)

    urls_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        head=head,
        command_name=command_name,
        normalized_purls=normalized_purls,
        unique=unique,
        purl_warnings=urls_warnings,
    )

    return urls_details


def make_head_request(url_detail):
    """
    Make a head request (and as noted below, a get request as well, at least
    for now) and return a dictionary containing status code data for the
    incoming PURL URL.

    For now, this returns both get and head request status code data so the
    user can evaluate -- requests.get() and requests.head() sometimes return
    different status codes and sometimes return inaccurate codes, e.g., a
    404 when the URL actually exists.
    """
    if url_detail is None:
        return {"get_request": "N/A", "head_request": "N/A"}

    get_response = requests.get(url_detail)
    get_request_status_code = get_response.status_code

    head_response = requests.head(url_detail)
    head_request_status_code = head_response.status_code

    # Return a dictionary for readability.
    return {
        "get_request": get_request_status_code,
        "head_request": head_request_status_code,
    }


def check_urls_purl(purl):
    """
    If applicable, return a variable indicating that the input PURL is invalid,
    or its type is not supported (or not fully supported) by `urls`, or it
    does not exist in the upstream repo.
    """
    check_validation = validate_purl(purl)
    if check_validation is None:
        return "validation_error"
    results = check_validation

    if results["valid"] == False:
        return "not_valid"

    # Both of these lists are manually constructed from a visual inspection of
    # packageurl-python/src/packageurl/contrib/purl2url.py.

    #  This list applies to the purl2url.py `repo_url` section:
    urls_supported_ecosystems_repo_url = [
        "bitbucket",
        "cargo",
        "gem",
        "github",
        "gitlab",
        "golang",
        "hackage",
        "npm",
        "nuget",
        "pypi",
        "rubygems",
    ]

    #  This list applies to the purl2url.py `download_url` section:
    urls_supported_ecosystems_download_url = [
        "bitbucket",
        "cargo",
        "gem",
        "github",
        "gitlab",
        "hackage",
        "npm",
        "nuget",
        "rubygems",
    ]

    urls_purl = PackageURL.from_string(purl)

    if (
        urls_purl.type not in urls_supported_ecosystems_repo_url
        and urls_purl.type not in urls_supported_ecosystems_download_url
    ):
        return "valid_but_not_supported"

    if results["exists"] == False:
        return "not_in_upstream_repo"

    if (
        urls_purl.type in urls_supported_ecosystems_repo_url
        and urls_purl.type not in urls_supported_ecosystems_download_url
    ) or (
        urls_purl.type not in urls_supported_ecosystems_repo_url
        and urls_purl.type in urls_supported_ecosystems_download_url
    ):

        return "valid_but_not_fully_supported"


@purlcli.command(name="validate")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    metavar="PURL",
    required=False,
    help="Package-URL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    metavar="FILE",
    required=False,
    default="-",
    show_default=True,
    help="Write output as JSON to FILE. Default is to print on screen.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    metavar="FILE",
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
@click.option(
    "--unique",
    is_flag=True,
    required=False,
    help="Return data only for unique PURLs.",
)
def validate(purls, output, file, unique):
    """
    Validate PURL syntax and existence.

    Check that the syntax of a PURL is correct. Check that the PURL exists using the PurlDB.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    validated_purls = get_validate_details(purls, output, file, unique, command_name)
    json.dump(validated_purls, output, indent=4)


def get_validate_details(purls, output, file, unique, command_name):
    """
    Return a dictionary containing validation data for each PURL in the `purls`
    input list.
    """
    validate_details = {}
    validate_details["headers"] = []

    validate_warnings = {}

    input_purls, normalized_purls = normalize_purls(purls, unique)

    validate_details["packages"] = []

    clear_log_file()

    for purl in input_purls:
        purl = purl.strip()
        if not purl:
            continue

        validated_purl = check_validate_purl(purl)

        if command_name == "validate" and validated_purl in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
            "check_existence_not_supported",
        ]:
            validate_warnings[purl] = validated_purl

        if validated_purl:
            validate_details["packages"].append(validate_purl(purl))

    validate_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        command_name=command_name,
        normalized_purls=normalized_purls,
        unique=unique,
        purl_warnings=validate_warnings,
    )

    return validate_details


def check_validate_purl(purl):
    """
    As applicable, return a variable indicating that the input PURL is
    valid/invalid or does not exist in the upstream repo.
    """
    check_validation = validate_purl(purl)
    if check_validation is None:
        return "validation_error"
    results = check_validation

    if results["valid"] == False:
        return "not_valid"

    if results["exists"] == False:
        return "not_in_upstream_repo"

    if results["exists"] == True:
        return check_validation

    if results["exists"] == None:
        return "check_existence_not_supported"


def validate_purl(purl):
    """
    Return a JSON object containing data from the PurlDB `validate` endpoint
    regarding the validity of the input PURL.

    Based on packagedb.package_managers VERSION_API_CLASSES_BY_PACKAGE_TYPE
    and packagedb/api.py class PurlValidateViewSet(viewsets.ViewSet)
    -- and supported by testing the command -- it appears that the `validate`
    command `check_existence` parameter supports the following PURL types:

    "cargo",
    "composer",
    "deb",
    "gem",
    "golang",
    "hex",
    "maven",
    "npm",
    "nuget",
    "pypi",
    """
    logger = logging.getLogger(__name__)

    api_query = "https://public.purldb.io/api/validate/"
    request_body = {"purl": purl, "check_existence": True}

    try:
        response = requests.get(api_query, params=request_body).json()

    except json.decoder.JSONDecodeError as e:

        print(f"validate_purl(): json.decoder.JSONDecodeError for '{purl}': {e}")

        logging.basicConfig(
            filename=LOG_FILE_LOCATION,
            level=logging.ERROR,
            format="%(levelname)s - %(message)s",
            filemode="w",
        )

        logger.error(f"validate_purl(): json.decoder.JSONDecodeError for '{purl}': {e}")

    except Exception as e:
        print(f"'validate' endpoint error for '{purl}': {e}")

    else:
        if response is None:
            print(f"'{purl}' -- response.status_code for None = {response.status_code}")
        return response


@purlcli.command(name="versions")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    metavar="PURL",
    required=False,
    help="Package-URL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    metavar="FILE",
    required=False,
    default="-",
    show_default=True,
    help="Write output as JSON to FILE. Default is to print on screen.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    metavar="FILE",
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
@click.option(
    "--unique",
    is_flag=True,
    required=False,
    help="Return data only for unique PURLs.",
)
def get_versions(purls, output, file, unique):
    """
    List all known versions for a PURL.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    purl_versions = get_versions_details(purls, output, file, unique, command_name)
    json.dump(purl_versions, output, indent=4)


def get_versions_details(purls, output, file, unique, command_name):
    """
    Return a list of dictionaries containing version-related data for each PURL
    in the `purls` input list.  `check_versions_purl()` will print an error
    message to the console (also displayed in the JSON output) when necessary.
    """
    versions_details = {}
    versions_details["headers"] = []
    versions_details["packages"] = []

    versions_warnings = {}

    input_purls, normalized_purls = normalize_purls(purls, unique)

    clear_log_file()

    for purl in input_purls:
        purl = purl.strip()
        if not purl:
            continue

        purl_data = {}
        purl_data["purl"] = purl

        versions_purl = check_versions_purl(purl)

        if command_name == "versions" and versions_purl:
            versions_warnings[purl] = versions_purl
            continue

        version_collection = collect_versions(purl)

        purl_data["versions"] = version_collection
        versions_details["packages"].append(purl_data)

    versions_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        command_name=command_name,
        normalized_purls=normalized_purls,
        unique=unique,
        purl_warnings=versions_warnings,
    )

    return versions_details


def collect_versions(purl):
    """
    Return a list of version objects collected from fetchcode/package_versions.py.
    """
    collected_versions = []
    for package_version in list(versions(purl)):
        purl_version_data = {}
        purl_version = package_version.value

        # We use `versions()` from fetchcode/package_versions.py, which
        # keeps the version (if any) of the input PURL in its output, so
        # "pkg:pypi/fetchcode@0.3.0" is returned as
        # "pkg:pypi/fetchcode@0.3.0@0.1.0", "pkg:pypi/fetchcode@0.3.0@0.2.0"
        # etc.  Thus, we remove any string starting with `@` first.
        raw_purl = purl = re.split("[@,]+", purl)[0]
        nested_purl = raw_purl + "@" + f"{purl_version}"

        purl_version_data["purl"] = nested_purl
        purl_version_data["version"] = f"{purl_version}"
        purl_version_data["release_date"] = f"{package_version.release_date}"

        collected_versions.append(purl_version_data)

    return collected_versions


def check_versions_purl(purl):
    """
    Return a variable identifying the message for printing to the console by
    get_versions_details() if (1) the input PURL is invalid, (2) its type is not
    supported by `versions` or (3) its existence was not validated (e.g.,
    "does not exist in the upstream repo").

    This message will also be reported by construct_headers() in the
    `warnings` field of the `header` section of the JSON object returned by
    the `versions` command.

    Note for dev purposes: SUPPORTED_ECOSYSTEMS (imported from
    fetchcode.package_versions) comprises the following types:
    [
        "cargo",
        "composer",
        "conan",
        "deb",
        "gem",
        "github",
        "golang",
        "hex",
        "maven",
        "npm",
        "nuget",
        "pypi",
    ]
    """
    check_validation = validate_purl(purl)
    if check_validation is None:
        return "validation_error"
    results = check_validation

    if results["valid"] == False:
        return "not_valid"

    supported = SUPPORTED_ECOSYSTEMS
    versions_purl = PackageURL.from_string(purl)

    if versions_purl.type not in supported:
        return "valid_but_not_supported"

    if results["exists"] == False:
        return "not_in_upstream_repo"

    if results["exists"] == None:
        return "check_existence_not_supported"

    # This handles the conflict between the `validate`` endpoint (treats
    # both "pkg:deb/debian/2ping" and "pkg:deb/2ping" as valid) and
    # fetchcode.package_versions versions() (returns None for "pkg:deb/2ping").
    if versions(purl) is None:
        return "valid_but_not_supported"


def check_for_duplicate_input_sources(purls, file):
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")


def clear_log_file():
    log_file = Path(LOG_FILE_LOCATION)

    if log_file.is_file():
        os.remove(log_file)


class D2DPackage(NamedTuple):
    """
    A package to use in d2d, identifier by its PURL and qualified by is package_content which is one
    of PackageContentType.
    """
    purl: str
    package_content: str
    download_url: str

    def __repr__(self) -> str:
        return f"{self.purl!r}"


def get_packages_by_set(purl, purldb_api_url):
    """
    Yield list of D2DPackages for each package_set of a purl.
    """
    package_api_url = get_package(purl, purldb_api_url)
    package_api_url = package_api_url.get("results")[0]
    if not package_api_url:
        return
    for package_set in package_api_url.get("package_sets") or []:
        packages = []
        for package_api_url in package_set.get("packages") or []:
            package_response = requests.get(package_api_url)
            package_data = package_response.json()
            p = D2DPackage(
                purl=package_data.get("purl"),
                package_content=package_data.get("package_content"),
                download_url=package_data.get("download_url"),
            )
            packages.append(p)
        yield packages


class PackagePair(NamedTuple):
    """
    A pair of from and to D2DPackages.=
    """
    from_package: D2DPackage
    to_package: D2DPackage

    def __repr__(self) -> str:
        return f"{self.from_package!r} -> {self.to_package!r}"


# Keep in sync with the packagedb.models.PackageContentType
class PackageContentType(Enum):
    SOURCE_REPO = 3, 'source_repo'
    SOURCE_ARCHIVE = 4, 'source_archive'
    BINARY = 5, 'binary'


def generate_d2d_package_pairs(from_packages, to_packages):
    """
    Yield PackagePair objects based on all the combinations of ``from_packages`` and ``to_packages``
    D2DPackage lists.
    """

    for from_package in from_packages:
        for to_package in to_packages:
            yield PackagePair(from_package=from_package, to_package=to_package)


def get_package_pairs_for_d2d(packages):
    """
    Yield PackagePair objects from a ``packages`` list of D2DPackage.
    The approach is to yield:
    - a pair for each (source repo, source archive)
    - a pair for each (source repo or source archive, binary archive)
    """
    packages = sorted(packages, key=lambda p: p.package_content)

    packages_by_content = {}

    for content, content_packages in groupby(packages, key=lambda p: p.package_content):
        packages_by_content[content] = list(content_packages)

    source_repo_packages = packages_by_content.get(PackageContentType.SOURCE_REPO.name.lower(), [])
    source_archive_packages = packages_by_content.get(PackageContentType.SOURCE_ARCHIVE.name.lower(), [])
    binary_packages = packages_by_content.get(PackageContentType.BINARY.name.lower(), [])

    yield from generate_d2d_package_pairs(from_packages=source_repo_packages, to_packages=binary_packages)
    yield from generate_d2d_package_pairs(from_packages=source_archive_packages, to_packages=binary_packages)
    yield from generate_d2d_package_pairs(from_packages=source_repo_packages, to_packages=source_archive_packages)


def validate_purls_for_d2d(ctx, param, value):
    """
    Validate a ``value`` list of PURls or URLs as suitable for d2d.
    """
    purls = value
    len_purls = len(purls)
    if len_purls > 2:
        raise click.BadParameter("Invalid number of --purl options. Only one or two options are allowed.")

    if len_purls == 1:
        if not purls[0].startswith("pkg:"):
            raise click.BadParameter(f"Invalid PURL: {purls[0]!r}. Must start with `pkg:`")
        else:
            return value

    elif len_purls != 2:
        raise click.BadParameter(f"Invalid number of --purl options. There should be exactly two --purl options.")

    elif not (all_purls(purls) or all_urls(purls)):
        purls = '\n'.join(purls)
        raise click.BadParameter(
            f"Invalid combination of --purl options:\n"
            f"{purls}\n"
            "Can be either two PURLs or two HTTP URLs, not a mix of PURLs and URLs.",
        )
    return value


def all_purls(purls):
    return all(p.startswith("pkg:") for p in purls)


def all_urls(purls):
    return all(p.startswith("http") for p in purls)


@purlcli.command(name="d2d")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    metavar="PURL",
    callback=validate_purls_for_d2d,
    help="Package-URL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    metavar="FILE",
    required=False,
    default="-",
    show_default=True,
    help="Write output as JSON to FILE. Default is to print on screen.",
)
@click.option(
    "--purldb-api-url",
    metavar="URL",
    required=False,
    default="https://public.purldb.io/api",
    show_default=True,
    help="PurlDB API URL.",
)
@click.option(
    "--matchcode-api-url",
    metavar="URL",
    required=False,
    default="https://matchcode.io/api",
    show_default=True,
    help="MatchCode API URL.",
)
def d2d(purls, output, purldb_api_url, matchcode_api_url):
    """
    Run deploy-to-devel "back2source" analysis between packages.

    The behavior depends on the number of --purl options and their values.

    With a single PURL, run the deploy-to-devel between all the PURLs of the set of PURLs  that
    this PURL belongs to.

    With two PURLs, run the deploy-to-devel between these two PURLs. The first is the "from" PURL,
    and the second is the "to" PURL.

    The first or "from" PURL is typically the source code or version control checkout. The second or
    "to" PURL is the target of a build or transformnation such as a binary, or a source archive.

    You can also provide two HTTP URLs instead of PURLs and  use these as direct download URLs.

    This command waits for the run to complete and save results to the `output` FILE.
    """
    if len(purls) == 1:
        # this must be a PURL for set
        purl = purls[0]
        d2d_results = run_d2d_purl_set(
            purl=purl,
            purldb_api_url=purldb_api_url,
            matchcode_api_url=matchcode_api_url,
        )
        return json.dump(d2d_results, output, indent=4)

    # by construction we now have either two purls or two urls
    if all_purls(purls):
        from_purl, to_purl = purls
        run_id, project_url = map_deploy_to_devel(
            from_purl=from_purl,
            to_purl=to_purl,
            purldb_api_url=purldb_api_url,
            matchcode_api_url=matchcode_api_url,
        )

    elif all_urls(purls):
        from_url, to_url = purls
        run_id, project_url = map_deploy_to_devel_urls(
            from_url=from_url,
            to_url=to_url,
            matchcode_api_url=matchcode_api_url,
        )

    else:
        # this should never happen
        raise click.BadParameter("Invalid PURLs or URLs combination.")

    # poll every 5 seconds to get results back
    while True:
        # TODO: Use a better progress indicator.
        sys.stderr.write(".")
        data = get_run_data(run_id=run_id, matchcode_api_url=matchcode_api_url)
        if data.get("status") != "running":
            break
        time.sleep(5)

    results = get_project_results(project_url=project_url)
    json.dump(results, output, indent=4)


def get_run_data(run_id, matchcode_api_url):
    """
    Fetch and return the latest d2d run data for a ``run_id``.
    """
    url = urljoin(matchcode_api_url, f"runs/{run_id}/")
    response = requests.get(url)
    data = response and response.json() or {}
    return data


def get_project_results(project_url):
    """
    Fetch and return the results of a project.
    """
    response = requests.get(project_url)
    data = response and response.json() or {}
    return data


@dataclass
class D2DProject:
    project_url: str
    done: bool
    package_pair: PackagePair
    result: dict
    run_id: str


def run_d2d_purl_set(purl, purldb_api_url, matchcode_api_url):
    """
    Run deploy-to-devel between all the packages of a PURL set. Return a list of result mappings,
    one for each pair of PURLs.

    The PURLs in a set typically include the source code archives, version control checkouts, and
    various binary pre-built archives. This command runs a deploy-to-devel between all related pairs
    of PURls in a set including all source-to-binary and all source-to-source pairs.

    This command waidefts for the run to complete to return the results.
    """
    projects: list[D2DProject] = []
    for d2d_packages in get_packages_by_set(purl, purldb_api_url):
        package_pairs = get_package_pairs_for_d2d(d2d_packages)
        for package_pair in package_pairs:
            click.echo(f"Running D2D for: {package_pair.from_package.purl} -> {package_pair.to_package.purl}", err=True)
            run_id, project_url = map_deploy_to_devel(
                from_purl=package_pair.from_package.purl,
                to_purl=package_pair.to_package.purl,
                purldb_api_url=purldb_api_url,
                matchcode_api_url=matchcode_api_url,
            )
            d2d_project = D2DProject(
                project_url=project_url,
                done=False,
                run_id=run_id,
                package_pair=package_pair,
                result={},
            )
            projects.append(d2d_project)

    while True:
        for project in projects:
            if project.done:
                continue
            # TODO: Use a better progress indicator.
            click.echo(".", err=True)
            data = get_run_data(matchcode_api_url=matchcode_api_url, run_id=run_id)
            if data.get("status") != "running":
                project.done = True
                project.result = get_project_results(project_url=project.project_url)
            time.sleep(1)
        time.sleep(5)
        if all(project.done for project in projects):
            break

    d2d_results = []
    for project in projects:
        d2d_results.append({
            "results": {
                "from": {
                    "purl": project.package_pair.from_package.purl,
                    "package_content": project.package_pair.from_package.package_content,
                    "download_url": project.package_pair.from_package.download_url
                },
                "to": {
                    "purl": project.package_pair.to_package.purl,
                    "package_content": project.package_pair.to_package.package_content,
                    "download_url": project.package_pair.to_package.download_url
                },
                "d2d_result": project.result
            }
        })
    return d2d_results


def map_deploy_to_devel(from_purl, to_purl, purldb_api_url, matchcode_api_url):
    """
    Return a tuple of matchcode.io d2d (run ID, project URL) for a given pair of PURLs.
    Raise an exception if we can not find download URLs for the PURLs.
    """
    from_url = get_download_url(purl=from_purl, purldb_api_url=purldb_api_url)
    if not from_url:
        raise Exception(f"Could not find download URL for the `from` PURL: {from_purl}.")

    to_url = get_download_url(purl=to_purl, purldb_api_url=purldb_api_url)
    if not to_url:
        raise Exception(f"Could not find download URL for the `to` PURL: {to_url}.")

    return map_deploy_to_devel_urls(
        from_url=from_url,
        to_url=to_url,
        matchcode_api_url=matchcode_api_url,
    )


def map_deploy_to_devel_urls(from_url, to_url, matchcode_api_url):
    """
    Return a tuple of matchcode.io d2d (run ID, project URL) for a given pair of HTTP URLs.
    """
    input_urls = (f"{from_url}#from", f"{to_url}#to",)

    d2d_launch = launch_d2d(input_urls=input_urls, matchcode_api_url=matchcode_api_url)
    project_url = d2d_launch.get("url") or None
    run_url = d2d_launch.get("runs")
    if not run_url:
        raise Exception(f"Could not find a run URL for the input URLs {input_urls!r}.")

    return run_url[0], project_url


def launch_d2d(matchcode_api_url, input_urls):
    """
    Launch d2d and return a mapping of run details.
    These are used for polling and fetching results later.
    """
    url = urljoin(matchcode_api_url, "d2d/")
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({"input_urls":input_urls, "runs":[]})
    d2d_results = requests.post(
        url=url,
        data=payload,
        headers=headers,
    )
    return d2d_results and d2d_results.json() or {}


def get_download_url(purl, purldb_api_url):
    """
    Return the download URL for a given PURL or None.
    """
    package = get_package(purl, purldb_api_url)
    package = package.get("results") or []
    if package:
        package = package[0]
    else:
        return None
    return package.get("download_url") or None


def get_package(purl, purldb_api_url):
    """
    Return a package mapping for a given PURL or an empty mapping.
    """
    url = urljoin(purldb_api_url, f"packages/?purl={purl}")
    response = requests.get(url=url)
    data = response.json()
    return data or {}


if __name__ == "__main__":
    purlcli()
