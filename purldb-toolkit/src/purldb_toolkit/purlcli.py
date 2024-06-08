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
from fetchcode.package_versions import versions
from packageurl.contrib import purl2url


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
    Fetch package metadata for a PURL.
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
    deduplicated_purls = deduplicate_purls(purls)

    for purl in deduplicated_purls:
        purl = purl.strip()
        if not purl:
            continue
        metadata_collection = collect_metadata(purl)
        metadata_details["packages"].extend(metadata_collection)

    metadata_details["headers"] = construct_headers(
        deduplicated_purls=deduplicated_purls,
        output=output,
        file=file,
        command_name=command_name,
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


def deduplicate_purls(purls):
    """
    Deduplicate all input PURLs.  PURLs with different versions or no version
    are treated as unique for purposes of deduplication.
    """
    reviewed = set()
    deduplicated_purls = []
    for purl in purls:
        purl = purl.strip()
        if purl not in reviewed:
            reviewed.add(purl)
            deduplicated_purls.append(purl)

    return deduplicated_purls


def construct_headers(
    deduplicated_purls=None,
    output=None,
    file=None,
    command_name=None,
    head=None,
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
    deduplicated_purls = deduplicate_purls(purls)

    for purl in deduplicated_purls:
        url_detail = {}
        url_detail["purl"] = purl
        purl = purl.strip()
        if not purl:
            continue

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
        output=output,
        file=file,
        head=head,
        command_name=command_name,
    )

    return urls_details


def make_head_request(url_detail):
    """
    Return both get and head request status code data for each URL.
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
    Validate PURL syntax and existence.

    Check that the syntax of a PURL is correct. Check that the PURL exists using the PurlDB.
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
    validate_details["packages"] = []
    deduplicated_purls = deduplicate_purls(purls)

    for purl in deduplicated_purls:
        purl = purl.strip()
        if not purl:
            continue

        original_validate_purl = validate_purl(purl)
        reordered_validate_purl = {
            "purl": original_validate_purl.pop("purl"),
            **original_validate_purl,
        }
        validate_details["packages"].append(reordered_validate_purl)

    validate_details["headers"] = construct_headers(
        deduplicated_purls=deduplicated_purls,
        output=output,
        file=file,
        command_name=command_name,
    )

    return validate_details


def validate_purl(purl):
    """
    Return a JSON object containing data from the PurlDB `validate` endpoint
    regarding the validity of the input PURL.
    """
    api_query = "https://public.purldb.io/api/validate/"
    request_body = {"purl": purl, "check_existence": True}
    response = requests.get(api_query, params=request_body).json()

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
    List all known versions for a PURL.
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

    raw_purls = []
    for input_purl in purls:
        raw_purl = re.split("[@,]+", input_purl)[0]
        raw_purls.append(raw_purl)

    deduplicated_purls = deduplicate_purls(raw_purls)
    for deduplicated_purl in deduplicated_purls:
        deduplicated_purl = deduplicated_purl.strip()
        if not deduplicated_purl:
            continue
        purl_data = {}
        purl_data["purl"] = deduplicated_purl

        version_collection = collect_versions(deduplicated_purl)
        versions_details["packages"].extend(version_collection)

    versions_details["headers"] = construct_headers(
        deduplicated_purls=purls,
        output=output,
        file=file,
        command_name=command_name,
    )

    return versions_details


def collect_versions(purl):
    """
    Return a list of version objects for each input PURL.
    """
    collected_versions = []
    for package_version in list(versions(purl)):
        purl_version_data = {}
        purl_version = package_version.value

        purl_version_data["purl"] = purl
        purl_version_data["version"] = f"{purl_version}"

        pkg_ver_release_date_no_time = None
        if package_version.release_date:
            pkg_ver_release_date = package_version.release_date
            pkg_ver_release_date_no_time = str(pkg_ver_release_date.date())
            purl_version_data["release_date"] = f"{pkg_ver_release_date_no_time}"

        purl_version_data["release_date"] = pkg_ver_release_date_no_time
        collected_versions.append(purl_version_data)

    return collected_versions


def check_for_duplicate_input_sources(purls, file):
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")
    elif not (purls or file):
        raise click.UsageError("Use either purls or file.")


if __name__ == "__main__":
    purlcli()
