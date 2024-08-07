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
from fetchcode.package_versions import versions
from packageurl.contrib import purl2url

# in seconds
POLLING_INTERVAL = 5


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
    purl_metadata = info(purl)
    if purl_metadata:
        for release in list(purl_metadata):
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

    # poll every fewseconds to get results back
    while True:
        # TODO: Use a better progress indicator.
        sys.stderr.write(".")
        data = get_run_data(run_id=run_id, matchcode_api_url=matchcode_api_url)
        if data.get("status") != "running":
            break
        time.sleep(POLLING_INTERVAL)

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
        time.sleep(POLLING_INTERVAL)
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
