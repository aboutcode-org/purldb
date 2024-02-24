#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import re
from importlib.metadata import version

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS, versions
from packageurl import PackageURL
from packageurl.contrib import purl2url

from packagedb.package_managers import VERSION_API_CLASSES_BY_PACKAGE_TYPE


@click.group()
def purlcli():
    """
    Return information from a PURL.
    """


@purlcli.command(name="metadata")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    required=False,
    help="PackageURL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    required=True,
    default="-",
    help="Write meta output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
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
    Given one or more PURLs, for each PURL, return a mapping of metadata
    fetched from the fetchcode package.py info() function.
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

    normalized_purls = []
    input_purls = []
    if unique:
        for purl in purls:
            purl, normalized_purl = normalize_purl(purl)
            normalized_purls.append((purl, normalized_purl))
            if normalized_purl not in input_purls:
                input_purls.append(normalized_purl)
    else:
        input_purls = purls

    for purl in input_purls:
        purl = purl.strip()
        if not purl:
            continue

        metadata_purl = check_metadata_purl(purl)

        if command_name == "metadata" and metadata_purl == "not_valid":
            print(f"'{purl}' not valid")
            continue

        if command_name == "metadata" and metadata_purl == "valid_but_not_supported":
            print(f"'{purl}' not supported with `metadata` command")
            continue

        if command_name == "metadata" and metadata_purl == "not_in_upstream_repo":
            print(f"'{purl}' does not exist in the upstream repo")
            continue

        for release in list(info(purl)):
            release_detail = release.to_dict()
            release_detail.move_to_end("purl", last=False)
            metadata_details["packages"].append(release_detail)

    metadata_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        command_name=command_name,
        normalized_purls=normalized_purls,
        unique=unique,
    )

    return metadata_details


def normalize_purl(purl):
    """
    Remove substrings that start with the '@', '?' or '#' separators.
    """
    input_purl = purl
    purl = purl.strip()
    purl = re.split("[@,?,#,]+", purl)[0]
    normalized_purl = purl

    return input_purl, normalized_purl


def construct_headers(
    purls=None,
    output=None,
    file=None,
    command_name=None,
    head=None,
    normalized_purls=None,
    unique=None,
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

    if (command_name in ["metadata", "urls"]) and unique:
        for purl in normalized_purls:
            if purl[0] != purl[1]:
                warnings.append(f"input PURL: '{purl[0]}' normalized to '{purl[1]}'")

    for purl in purls:
        if not purl:
            continue

        # `metadata` warnings:
        metadata_purl = check_metadata_purl(purl)

        if command_name == "metadata" and metadata_purl == "not_valid":
            warnings.append(f"'{purl}' not valid")
            continue

        if command_name == "metadata" and metadata_purl == "valid_but_not_supported":
            warnings.append(f"'{purl}' not supported with `metadata` command")
            continue

        if command_name == "metadata" and metadata_purl == "not_in_upstream_repo":
            warnings.append(f"'{purl}' does not exist in the upstream repo")
            continue

        # `urls` warnings:
        urls_purl = check_urls_purl(purl)

        if command_name == "urls" and urls_purl == "not_valid":
            warnings.append(f"'{purl}' not valid")
            continue

        if command_name == "urls" and urls_purl == "valid_but_not_supported":
            warnings.append(f"'{purl}' not supported with `urls` command")
            continue

        if command_name == "urls" and urls_purl == "valid_but_not_fully_supported":
            warnings.append(f"'{purl}' not fully supported with `urls` command")

        if command_name == "urls" and urls_purl == "not_in_upstream_repo":
            warnings.append(f"'{purl}' does not exist in the upstream repo")
            continue

    headers_content["errors"] = errors
    headers_content["warnings"] = warnings
    headers.append(headers_content)

    return headers


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
    results = validate_purls([purl])[0]

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


@purlcli.command(name="urls")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    required=False,
    help="PackageURL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    required=True,
    default="-",
    help="Write urls output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
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
    Given one or more PURLs, for each PURL, return a list of all known URLs
    fetched from the packageurl-python purl2url.py code.
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

    normalized_purls = []
    input_purls = []
    if unique:
        for purl in purls:
            purl, normalized_purl = normalize_purl(purl)
            normalized_purls.append((purl, normalized_purl))
            if normalized_purl not in input_purls:
                input_purls.append(normalized_purl)
    else:
        input_purls = purls

    for purl in input_purls:
        url_detail = {}
        url_detail["purl"] = purl

        purl = purl.strip()
        if not purl:
            continue

        urls_purl = check_urls_purl(purl)

        # Print warnings to terminal.
        if command_name == "urls" and urls_purl == "not_valid":
            print(f"'{purl}' not valid")
            continue

        if command_name == "urls" and urls_purl == "valid_but_not_supported":
            print(f"'{purl}' not supported with `urls` command")
            continue

        if command_name == "urls" and urls_purl == "valid_but_not_fully_supported":
            print(f"'{purl}' not fully supported with `urls` command")

        if command_name == "urls" and urls_purl == "not_in_upstream_repo":
            print(f"'{purl}' does not exist in the upstream repo")
            continue

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
    results = validate_purls([purl])[0]

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


# Not yet converted to a SCTK-like data structure.
@purlcli.command(name="validate")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    required=False,
    help="PackageURL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    required=True,
    default="-",
    help="Write validation output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
def validate(purls, output, file):
    """
    Check the syntax of one or more PURLs.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    validated_purls = validate_purls(purls)
    json.dump(validated_purls, output, indent=4)


def validate_purls(purls):
    """
    Return a JSON object containing data regarding the validity of the input PURL.

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
    api_query = "https://public.purldb.io/api/validate/"
    validated_purls = []
    for purl in purls:
        purl = purl.strip()
        if not purl:
            continue
        request_body = {"purl": purl, "check_existence": True}
        response = requests.get(api_query, params=request_body)
        # results = response.json()
        try:
            results = response.json()
        except:
            return
        validated_purls.append(results)

    return validated_purls


# Not yet converted to a SCTK-like data structure.
@purlcli.command(name="versions")
@click.option(
    "--purl",
    "purls",
    multiple=True,
    required=False,
    help="PackageURL or PURL.",
)
@click.option(
    "--output",
    type=click.File(mode="w", encoding="utf-8"),
    required=True,
    default="-",
    help="Write versions output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
def get_versions(purls, output, file):
    """
    Given one or more PURLs, return a list of all known versions for each PURL.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    purl_versions = list_versions(purls, output, file, command_name)
    json.dump(purl_versions, output, indent=4)


# construct_headers() has not yet been implemented for this `versions` command
# -- or for the `validate` command.
def list_versions(purls, output, file, command_name):
    """
    Return a list of dictionaries containing version-related data for each PURL
    in the `purls` input list.  `check_versions_purl()` will print an error
    message to the console (also displayed in the JSON output) when necessary.
    """
    purl_versions = []
    for purl in purls:
        purl_data = {}
        purl_data["purl"] = purl
        purl_data["versions"] = []

        purl = purl.strip()
        if not purl:
            continue

        versions_purl = check_versions_purl(purl)

        if command_name == "versions" and versions_purl == "not_valid":
            print(f"'{purl}' not valid")
            continue

        if command_name == "versions" and versions_purl == "valid_but_not_supported":
            print(f"'{purl}' not supported with `versions` command")
            continue

        if command_name == "versions" and versions_purl == "not_in_upstream_repo":
            print(f"'{purl}' does not exist in the upstream repo")
            continue

        # TODO: Add to warnings and test it as well.
        if command_name == "versions" and versions_purl == "error_fetching_purl":
            print(f"Error fetching '{purl}'")
            continue

        for package_version_object in list(versions(purl)):
            purl_version_data = {}
            purl_version = package_version_object.to_dict()["value"]
            nested_purl = purl + "@" + f"{purl_version}"

            purl_version_data["purl"] = nested_purl
            purl_version_data["version"] = f"{purl_version}"
            purl_version_data["release_date"] = (
                f'{package_version_object.to_dict()["release_date"]}'
            )

            purl_data["versions"].append(purl_version_data)

        purl_versions.append(purl_data)

    return purl_versions


def check_versions_purl(purl):
    """
    Return a message for printing to the console if the input PURL is invalid,
    its type is not supported by `versions` or its existence was not validated.

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
    results = validate_purls([purl])[0]

    if results is None:
        return "error_fetching_purl"

    if results["valid"] == False:
        return "not_valid"

    supported = SUPPORTED_ECOSYSTEMS

    versions_purl = PackageURL.from_string(purl)

    if versions_purl.type not in supported:
        return "valid_but_not_supported"

    if results["exists"] == False:
        return "not_in_upstream_repo"

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


if __name__ == "__main__":
    purlcli()
