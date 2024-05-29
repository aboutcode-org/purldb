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
from importlib.metadata import version
from pathlib import Path

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS
from fetchcode.package_versions import versions
from packageurl import PackageURL
from packageurl.contrib import purl2url

LOG_FILE_LOCATION = os.path.join(os.path.expanduser("~"), "purlcli.log")
logger = logging.getLogger(__name__)


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
def get_metadata(purls, output, file):
    """
    Given one or more PURLs, for each PURL, return a mapping of metadata
    fetched from the fetchcode package.py info() function.
    """
    check_for_duplicate_input_sources(purls, file)
    if file:
        purls = file.read().splitlines(False)
    context = click.get_current_context()
    command_name = context.command.name
    metadata_info = get_metadata_details(purls, output, file, command_name)
    json.dump(metadata_info, output, indent=4)


def get_metadata_details(purls, output, file, command_name):
    """
    Return a dictionary containing metadata for each PURL in the `purls` input
    list.
    """
    metadata_details = {}
    metadata_details["headers"] = []
    metadata_details["packages"] = []
    metadata_warnings = {}
    deduplicated_purls, duplicate_purls = deduplicate_purls(purls)
    clear_log_file()

    for purl in deduplicated_purls:
        purl = purl.strip()
        if not purl:
            continue
        metadata_purl_status = check_metadata_purl(purl)
        if command_name == "metadata" and metadata_purl_status in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
        ]:
            metadata_warnings[purl] = metadata_purl_status
            continue
        if command_name == "metadata" and metadata_purl_status in [
            "valid_but_not_fully_supported",
            "check_existence_not_supported",
        ]:
            metadata_warnings[purl] = metadata_purl_status
        metadata_collection = collect_metadata(purl)
        metadata_details["packages"].extend(metadata_collection)

    metadata_details["headers"] = construct_headers(
        deduplicated_purls=deduplicated_purls,
        duplicate_purls=duplicate_purls,
        output=output,
        file=file,
        command_name=command_name,
        purl_warnings=metadata_warnings,
    )
    return metadata_details


def collect_metadata(purl):
    """
    Return a list of release-based metadata collections (a fetchcode Package)
    from fetchcode/package.py.
    """
    collected_metadata = []
    for release in list(info(purl)):
        if release is None:
            continue
        release_detail = release.to_dict()
        release_detail.move_to_end("purl", last=False)
        collected_metadata.append(release_detail)
    return collected_metadata


def check_metadata_purl(purl):
    """
    Return a variable identifying the warning if (1) the input PURL is invalid,
    (2) its type is not supported by `metadata` or (3) its existence was not
    validated (e.g., "does not exist in the upstream repo").  This will be
    reported by construct_headers() in the `warnings` field of the `header`
    section of the JSON object returned by the `metadata` command.
    """
    check_validation = validate_purl(purl)
    if check_validation is None:
        return "validation_error"
    elif check_validation["valid"] == False:
        return "not_valid"

    # This is manually constructed from a visual inspection of fetchcode/package.py.
    metadata_supported_ecosystems = [
        "bitbucket",
        "cargo",
        "generic",
        "github",
        "gnu",
        "npm",
        "openssl",
        "pypi",
        "rubygems",
        # NOTE: cocoapods support added subject to fetchcode/package.py PR approval and new release.
        "cocoapods",
    ]
    metadata_purl = PackageURL.from_string(purl)

    if metadata_purl.type not in metadata_supported_ecosystems:
        return "valid_but_not_supported"
    elif check_validation["exists"] == False:
        return "not_in_upstream_repo"
    elif check_validation["exists"] == None:
        return "check_existence_not_supported"


def deduplicate_purls(purls):
    """
    Deduplicate all input PURLs.  PURLs with different versions or no version
    are treated as unique for purposes of deduplication.
    """
    reviewed = set()
    deduplicated_purls = []
    duplicate_purls = []
    for purl in purls:
        purl = purl.strip()
        if purl not in reviewed:
            reviewed.add(purl)
            deduplicated_purls.append(purl)
        else:
            duplicate_purls.append(purl)
    return deduplicated_purls, duplicate_purls


def read_log_file(log_file_path):
    log_file = log_file_path
    if log_file.is_file():
        with open(log_file_path, "r") as log_file:
            return log_file.readlines()
    else:
        return []


def construct_headers(
    deduplicated_purls=None,
    duplicate_purls=None,
    output=None,
    file=None,
    command_name=None,
    head=None,
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

    context_purls = [p for p in deduplicated_purls]
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

    if isinstance(output, str):
        options["--output"] = output
    else:
        options["--output"] = output.name

    headers_content["options"] = options
    if command_name in ["metadata", "urls", "validate", "versions"]:
        if duplicate_purls:
            for duplicate in duplicate_purls:
                logger.warning(f"Duplicate input PURL removed: {duplicate}")

    for purl in deduplicated_purls:
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
                logger.warning(warning)
                continue

    log_file = Path(LOG_FILE_LOCATION)
    log_file_contents = read_log_file(log_file)
    if log_file_contents:
        for line in log_file_contents:
            if line.startswith("ERROR"):
                errors.append(line[8:-1])
            elif line.startswith("WARNING"):
                warnings.append(line[10:-1])

    headers_content["errors"] = errors
    headers_content["warnings"] = warnings
    headers.append(headers_content)
    return headers


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
    "--head",
    is_flag=True,
    required=False,
    help="Validate each URL's existence with a head request.",
)
def get_urls(purls, output, file, head):
    """
    Given one or more PURLs, for each PURL, return a list of all known URLs
    fetched from the packageurl-python purl2url.py code.
    """
    check_for_duplicate_input_sources(purls, file)
    if file:
        purls = file.read().splitlines(False)
    context = click.get_current_context()
    command_name = context.command.name
    urls_info = get_urls_details(purls, output, file, head, command_name)
    json.dump(urls_info, output, indent=4)


def get_urls_details(purls, output, file, head, command_name):
    """
    Return a dictionary containing URLs for each PURL in the `purls` input
    list.
    """
    urls_details = {}
    urls_details["headers"] = []
    urls_details["packages"] = []
    urls_warnings = {}
    deduplicated_purls, duplicate_purls = deduplicate_purls(purls)
    clear_log_file()

    for purl in deduplicated_purls:
        url_detail = {}
        url_detail["purl"] = purl
        purl = purl.strip()
        if not purl:
            continue
        urls_purl_status = check_urls_purl(purl)
        if command_name == "urls" and urls_purl_status in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
        ]:
            urls_warnings[purl] = urls_purl_status
            continue
        if command_name == "urls" and urls_purl_status in [
            "valid_but_not_fully_supported",
            "check_existence_not_supported",
        ]:
            urls_warnings[purl] = urls_purl_status

        url_purl = PackageURL.from_string(purl)

        url_detail["download_url"] = purl2url.get_download_url(purl)
        if head:
            url_detail["download_url"] = {"url": purl2url.get_download_url(purl)}

        url_detail["inferred_urls"] = [
            inferred for inferred in purl2url.get_inferred_urls(purl)
        ]
        if head:
            url_detail["inferred_urls"] = [
                {"url": inferred} for inferred in purl2url.get_inferred_urls(purl)
            ]

        url_detail["repository_download_url"] = purl2url.get_repo_download_url(purl)
        if head:
            url_detail["repository_download_url"] = {
                "url": purl2url.get_repo_download_url(purl)
            }

        url_detail["repository_homepage_url"] = purl2url.get_repo_url(purl)
        if head:
            url_detail["repository_homepage_url"] = {"url": purl2url.get_repo_url(purl)}

        url_list = [
            "download_url",
            "repository_download_url",
            "repository_homepage_url",
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
        deduplicated_purls=deduplicated_purls,
        duplicate_purls=duplicate_purls,
        output=output,
        file=file,
        head=head,
        command_name=command_name,
        purl_warnings=urls_warnings,
    )
    return urls_details


def make_head_request(url_detail):
    """
    Make a head request and get request and return a dictionary containing
    status code data for the incoming PURL URL.  This returns both get and
    head request status code data so the user can evaluate -- requests.get()
    and requests.head() sometimes return different status codes and sometimes
    return inaccurate codes, e.g., a 404 when the URL actually exists.
    """
    if url_detail is None:
        return {"get_request": "N/A", "head_request": "N/A"}
    get_response = requests.get(url_detail)
    get_request_status_code = get_response.status_code
    head_response = requests.head(url_detail)
    head_request_status_code = head_response.status_code
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
    # This list applies to the purl2url.py `repo_url` section:
    urls_supported_ecosystems_repo_url = [
        "bitbucket",
        "cargo",
        # NOTE: Temp for cocoapods dev work in purl2url.  Keep in the list uncommented -- I still need to respond to Tushar's comments but the real code work is done, now supported for repo_url.
        "cocoapods",
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
    if results["exists"] == None:
        return "check_existence_not_supported"


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
    Check the syntax and upstream repo status of one or more PURLs.
    """
    check_for_duplicate_input_sources(purls, file)
    if file:
        purls = file.read().splitlines(False)
    context = click.get_current_context()
    command_name = context.command.name
    validated_purls = get_validate_details(purls, output, file, command_name)
    json.dump(validated_purls, output, indent=4)


def get_validate_details(purls, output, file, command_name):
    """
    Return a dictionary containing validation data for each PURL in the `purls`
    input list.
    """
    validate_details = {}
    validate_details["headers"] = []
    validate_warnings = {}
    deduplicated_purls, duplicate_purls = deduplicate_purls(purls)
    validate_details["packages"] = []
    clear_log_file()

    for purl in deduplicated_purls:
        purl = purl.strip()
        if not purl:
            continue
        validated_purl_status = check_validate_purl(purl)
        if command_name == "validate" and validated_purl_status in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
            "check_existence_not_supported",
        ]:
            validate_warnings[purl] = validated_purl_status
        if validated_purl_status:
            # Move the `purl` key to the top.
            original_validate_purl = validate_purl(purl)
            reordered_validate_purl = {
                "purl": original_validate_purl.pop("purl"),
                **original_validate_purl,
            }
            validate_details["packages"].append(reordered_validate_purl)

    validate_details["headers"] = construct_headers(
        deduplicated_purls=deduplicated_purls,
        duplicate_purls=duplicate_purls,
        output=output,
        file=file,
        command_name=command_name,
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
    elif check_validation["valid"] == False:
        return "not_valid"
    elif check_validation["exists"] == False:
        return "not_in_upstream_repo"
    elif check_validation["exists"] == True:
        return check_validation
    elif check_validation["exists"] == None:
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
    logging.basicConfig(
        level=logging.WARN,
        format="%(levelname)s - %(message)s",
        filename=LOG_FILE_LOCATION,
        filemode="w",
    )

    api_query = "https://public.purldb.io/api/validate/"
    request_body = {"purl": purl, "check_existence": True}

    try:
        response = requests.get(api_query, params=request_body).json()
    except json.decoder.JSONDecodeError as e:
        logger.error(f"validate_purl(): json.decoder.JSONDecodeError for '{purl}': {e}")
    except Exception as e:
        logger.error(f"'validate' endpoint error for '{purl}': {e}")
    else:
        if response is None:
            logger.error(
                f"'{purl}' -- response.status_code for None = {response.status_code}"
            )
        return response


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
    purl_versions = get_versions_details(purls, output, file, command_name)
    json.dump(purl_versions, output, indent=4)


def get_versions_details(purls, output, file, command_name):
    """
    Return a list of dictionaries containing version-related data for each PURL
    in the `purls` input list.
    """
    versions_details = {}
    versions_details["headers"] = []
    versions_details["packages"] = []
    versions_warnings = {}
    deduplicated_purls, duplicate_purls = deduplicate_purls(purls)
    clear_log_file()

    for purl in deduplicated_purls:
        purl = purl.strip()
        if not purl:
            continue
        purl_data = {}
        purl_data["purl"] = purl
        versions_purl_status = check_versions_purl(purl)
        if command_name == "versions" and versions_purl_status in [
            "validation_error",
            "not_valid",
            "valid_but_not_supported",
            "not_in_upstream_repo",
        ]:
            versions_warnings[purl] = versions_purl_status
            continue
        if command_name == "versions" and versions_purl_status in [
            "valid_but_not_fully_supported",
            "check_existence_not_supported",
        ]:
            versions_warnings[purl] = versions_purl_status
        version_collection = collect_versions(purl)
        versions_details["packages"].extend(version_collection)

    versions_details["headers"] = construct_headers(
        deduplicated_purls=deduplicated_purls,
        duplicate_purls=duplicate_purls,
        output=output,
        file=file,
        command_name=command_name,
        purl_warnings=versions_warnings,
    )
    return versions_details


def collect_versions(purl):
    """
    Return a list of version objects collected from fetchcode/package_versions.py.

    We use `versions()` from fetchcode/package_versions.py, which keeps the
    version (if any) of the input PURL in its output, so
    "pkg:pypi/fetchcode@0.3.0" is returned as "pkg:pypi/fetchcode@0.3.0@0.1.0",
    "pkg:pypi/fetchcode@0.3.0@0.2.0" etc.  Thus, we remove any string starting
    with `@` first.
    """
    collected_versions = []
    for package_version in list(versions(purl)):
        purl_version_data = {}
        purl_version = package_version.value

        raw_purl = re.split("[@,]+", purl)[0]
        nested_purl = raw_purl + "@" + f"{purl_version}"
        pkg_ver_release_date = package_version.release_date
        pkg_ver_release_date_no_time = pkg_ver_release_date.date()

        purl_version_data["purl"] = nested_purl
        purl_version_data["version"] = f"{purl_version}"
        purl_version_data["release_date"] = f"{pkg_ver_release_date_no_time}"
        collected_versions.append(purl_version_data)
    return collected_versions


def check_versions_purl(purl):
    """
    Return a variable identifying the message for printing to the console by
    get_versions_details() if (1) the input PURL is invalid, (2) its type is not
    supported by `versions` or (3) its existence was not validated (e.g.,
    "does not exist in the upstream repo").  This message will also be reported
    by construct_headers() in the `warnings` field of the `header` section of
    the JSON object returned by the `versions` command.

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
    elif check_validation["valid"] == False:
        return "not_valid"

    supported = SUPPORTED_ECOSYSTEMS
    versions_purl = PackageURL.from_string(purl)
    if versions_purl.type not in supported:
        return "valid_but_not_supported"
    elif check_validation["exists"] == False:
        return "not_in_upstream_repo"
    elif check_validation["exists"] == None:
        return "check_existence_not_supported"
    # This handles the conflict between the `validate`` endpoint (treats
    # both "pkg:deb/debian/2ping" and "pkg:deb/2ping" as valid) and
    # fetchcode.package_versions versions() (returns None for "pkg:deb/2ping").
    elif versions(purl) is None:
        return "valid_but_not_supported"


def check_for_duplicate_input_sources(purls, file):
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")
    elif not (purls or file):
        raise click.UsageError("Use either purls or file.")


def clear_log_file():
    log_file = Path(LOG_FILE_LOCATION)
    with open(log_file, "w"):
        pass


if __name__ == "__main__":
    purlcli()
