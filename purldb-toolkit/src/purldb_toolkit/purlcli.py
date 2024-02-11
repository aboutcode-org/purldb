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


@purlcli.command(name="meta")
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
# TODO: need to strip versions, qualifiers and subpath data and note that in a warning.
def get_meta(purls, output, file):
    """
    Given one or more PURLs, for each PURL, return a mapping of metadata
    fetched from the fetchcode package.py info() function.

    Version information is not needed in submitted PURLs and if included will
    be removed before processing.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    manual_command_name = context.command.name
    command_name = context.command.name

    meta_info = get_meta_details(purls, output, file, command_name)
    json.dump(meta_info, output, indent=4)


def get_meta_details(purls, output, file, command_name):
    """
    Return a dictionary containing metadata for each PURL in the `purls` input
    list.  `check_meta_purl()` will print an error message to the console
    (also displayed in the JSON output) when necessary.
    """
    meta_details = {}
    # 2024-02-10 Saturday 13:40:43.  Move this to after the for loop so we can add stripped_purls.
    # meta_details["headers"] = construct_headers(
    #     purls=purls,
    #     output=output,
    #     file=file,
    #     command_name=command_name,
    # )
    # Create here so it appears before `packages`.
    meta_details["headers"] = []
    meta_details["packages"] = []

    processed_purls = []

    for purl in purls:
        if not purl:
            continue

        # Remove substrings that start with the '@', '?' or '#' separators.
        # purl = purl.strip()
        purl = strip_purl(purl)
        if purl not in processed_purls:
            processed_purls.append(purl)
        else:
            continue

        if command_name == "meta" and check_meta_purl(purl) == "not_valid":
            print(
                f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if (
            command_name == "meta"
            and check_meta_purl(purl) == "valid_but_not_supported"
        ):
            print(
                f"The provided PackageURL '{purl}' is valid, but `meta` does not support this package type."
            )
            continue

        if command_name == "meta" and check_meta_purl(purl) == "failed_to_fetch":
            print(
                f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
            )
            continue

        for release in list(info(purl)):
            release_detail = release.to_dict()
            release_detail.move_to_end("purl", last=False)
            meta_details["packages"].append(release_detail)

    print(f"\nprocessed_purls = {processed_purls}\n")
    # stripped = 'One or more input PURLs contain "@", "?" and/or "#" separators and have been stripped (starting with the separator) to enable proper processing.'
    # if stripped_purls:
    #     print(f'\n{stripped}')
    # meta_details["headers"] = construct_headers(
    #     purls=purls,
    #     output=output,
    #     file=file,
    #     command_name=command_name,
    # )
    meta_details["headers"].append(
        construct_headers(
            purls=purls,
            output=output,
            file=file,
            command_name=command_name,
            processed_purls=processed_purls,
        )
    )

    return meta_details


def strip_purl(purl):
    """
    Remove substrings that start with the '@', '?' or '#' separators.
    """
    # print(f"input PURL = {purl}")

    purl = purl.strip()
    purl = re.split("[@,?,#,]+", purl)[0]

    # print(f"stripped PURL = {purl}\n")

    return purl


# def construct_headers(purls=None, output=None, file=None, command_name=None, head=None):
def construct_headers(
    purls=None,
    output=None,
    file=None,
    command_name=None,
    head=None,
    processed_purls=None,
):
    """
    Return a list comprising the `headers` content of the dictionary output.
    """
    headers = []

    context_purls = [p for p in purls]
    context_file = file
    context_file_value = None
    if context_file:
        context_file_value = context_file.name

    headers_content = {}
    options = {}

    errors = []
    warnings = []

    headers_content["tool_name"] = "purlcli"
    headers_content["tool_version"] = version("purldb_toolkit")

    options["command"] = command_name
    options["--purl"] = context_purls
    options["--file"] = context_file_value
    if head:
        options["--head"] = True

    if isinstance(output, str):
        options["--output"] = output
    else:
        options["--output"] = output.name

    headers_content["options"] = options
    headers_content["purls"] = purls

    if command_name == "meta" and processed_purls:
        warnings.append(
            f"One or more input PURLs have been stripped to enable proper processing.  The final set of processed PURLs is listed in the 'processed_purls' field above."
        )

    for purl in purls:
        # Remove substrings that start with the '@', '?' or '#' separators.
        # purl = purl.strip()
        purl = strip_purl(purl)
        if not purl:
            continue

        # `meta` warnings:

        if command_name == "meta" and check_meta_purl(purl) == "not_valid":
            warnings.append(
                f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if (
            command_name == "meta"
            and check_meta_purl(purl) == "valid_but_not_supported"
        ):
            warnings.append(
                f"The provided PackageURL '{purl}' is valid, but `meta` does not support this package type."
            )
            continue

        if command_name == "meta" and check_meta_purl(purl) == "failed_to_fetch":
            warnings.append(
                f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
            )
            continue

        # `urls` warnings:

        if command_name == "urls" and check_urls_purl(purl) == "not_valid":
            warnings.append(
                f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if (
            command_name == "urls"
            and check_urls_purl(purl) == "valid_but_not_supported"
        ):
            warnings.append(
                f"The provided PackageURL '{purl}' is valid, but `urls` does not support this package type."
            )
            continue

        if (
            command_name == "urls"
            and check_urls_purl(purl) == "valid_but_not_fully_supported"
        ):
            warnings.append(
                f"The provided PackageURL '{purl}' is valid, but `urls` does not fully support this package type."
            )

    headers_content["processed_purls"] = processed_purls

    headers_content["errors"] = errors
    headers_content["warnings"] = warnings
    headers.append(headers_content)

    return headers


def check_meta_purl(purl):
    """
    Return a variable identifying the message for printing to the console by
    get_meta_details() if (1) the input PURL is invalid, (2) its type is not
    supported by `meta` or (3) its existence was not validated (e.g.,
    `Exception: Failed to fetch` or `Error while fetching`).

    This message will also be reported by construct_headers() in the
    `warnings` field of the `header` section of the JSON object returned by
    the `meta` command.
    """
    results = check_existence(purl)

    if results["valid"] == False:
        return "not_valid"

    # This is manually constructed from a visual inspection of fetchcode/package.py.
    meta_supported_ecosystems = [
        "bitbucket",
        "cargo",
        "github",
        "npm",
        "pypi",
        "rubygems",
    ]
    meta_purl = PackageURL.from_string(purl)

    if meta_purl.type not in meta_supported_ecosystems:
        return "valid_but_not_supported"

    if results["exists"] == False:
        return "failed_to_fetch"


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
# TODO: need to strip versions, qualifiers and subpath data and note that in a warning.
def get_urls(purls, output, file, head):
    """
    Given one or more PURLs, for each PURL, return a list of all known URLs
    fetched from the packageurl-python purl2url.py code.

    Version information is not needed in submitted PURLs and if included will
    be removed before processing.
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
    list.  `check_urls_purl()` will print an error message to the console
    (also displayed in the JSON output) when necessary.
    """
    urls_details = {}
    urls_details["headers"] = construct_headers(
        purls=purls,
        output=output,
        file=file,
        head=head,
        command_name=command_name,
    )

    urls_details["packages"] = []

    for purl in purls:
        url_detail = {}
        url_detail["purl"] = purl

        purl = purl.strip()
        if not purl:
            continue

        # Print warnings to terminal.

        if command_name == "urls" and check_urls_purl(purl) == "not_valid":
            print(
                f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if (
            command_name == "urls"
            and check_urls_purl(purl) == "valid_but_not_supported"
        ):
            print(
                f"The provided PackageURL '{purl}' is valid, but `urls` does not support this package type."
            )
            continue

        if (
            command_name == "urls"
            and check_urls_purl(purl) == "valid_but_not_fully_supported"
        ):
            print(
                f"The provided PackageURL '{purl}' is valid, but `urls` does not fully support this package type."
            )

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

    # Return a dictionary for best readability.
    return {
        "get_request": get_request_status_code,
        "head_request": head_request_status_code,
    }


# HEY 2024-02-02 Friday 09:31:27.  This has been simplified to return a short string that can be converted on the receiving end to a more nuanced message re the status of the PURL in question.
def check_urls_purl(purl):
    """
    If applicable, return a variable indicating that the input PURL is invalid,
    its type is not supported by `urls` or its existence was not validated.
    """
    results = check_existence(purl)

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

    if (
        urls_purl.type in urls_supported_ecosystems_repo_url
        and urls_purl.type not in urls_supported_ecosystems_download_url
    ) or (
        urls_purl.type not in urls_supported_ecosystems_repo_url
        and urls_purl.type in urls_supported_ecosystems_download_url
    ):

        return "valid_but_not_fully_supported"


# This code and the related tests have not yet been converted to a SCTK-like data structure.
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
# TODO: need to strip qualifiers and subpath data and note that in a warning.
def validate(purls, output, file):
    """
    Check the syntax of one or more PURLs.

    The validation process includes the `check_existence` step, which checks
    whether the package exists in the upstream repo.  Accordingly, version
    information can be included in the submitted PURLs and will be part of the
    validation process.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    # 2024-02-07 Wednesday 18:12:40.  Not yet!
    # context = click.get_current_context()
    # command_name = context.command.name

    validated_purls = validate_purls(purls)
    json.dump(validated_purls, output, indent=4)


def validate_purls(purls):
    api_query = "https://public.purldb.io/api/validate/"
    validated_purls = []
    for purl in purls:
        purl = purl.strip()
        if not purl:
            continue
        request_body = {"purl": purl, "check_existence": True}
        response = requests.get(api_query, params=request_body)
        results = response.json()
        validated_purls.append(results)

    # # from packagedb.package_managers import VERSION_API_CLASSES_BY_PACKAGE_TYPE
    # print(
    #     f"\n\nVERSION_API_CLASSES_BY_PACKAGE_TYPE = {VERSION_API_CLASSES_BY_PACKAGE_TYPE}"
    # )
    # print()
    # for k, v in VERSION_API_CLASSES_BY_PACKAGE_TYPE.items():
    #     print(f"{k} = {v}")
    # print()

    # # VERSION_API_CLASS_BY_PACKAGE_NAMESPACE
    # for k, v in VERSION_API_CLASS_BY_PACKAGE_NAMESPACE.items():
    #     print(f"{k} = {v}")

    return validated_purls


def check_existence(purl):
    """
    Return a JSON object containing data regarding the validity of the input PURL.
    """

    # 2/5/2024 5:59 PM Monday.  Based on packagedb.package_managers VERSION_API_CLASSES_BY_PACKAGE_TYPE -- and supported by testing the command -- it appears that the `validate` command `check_existence` check supports the following PURL types:

    # validate_supported_ecosystems = [
    # "cargo",
    # "composer",
    # "deb",
    # "gem",
    # "golang",
    # "hex",
    # "maven",
    # "npm",
    # "nuget",
    # "pypi",
    # ]

    api_query = "https://public.purldb.io/api/validate/"
    purl = purl.strip()
    request_body = {"purl": purl, "check_existence": True}
    response = requests.get(api_query, params=request_body)
    results = response.json()

    return results


# 2024-02-05 Monday 11:05:55.  Current output has this structure -- to be converted to SCTK-like structure.  These messages are defined in purldb/packagedb/api.py `class PurlValidateViewSet(viewsets.ViewSet)`.

# python -m purldb_toolkit.purlcli validate --purl pkg:pypi/@dejacode --purl pkg:pypi/dejacode@12345 --purl pkg:cargo/rand@0.7.2 --purl pkg:nginx/nginx@0.8.9?os=windows --output -
# [
#     {
#         "valid": false,
#         "exists": null,
#         "message": "The provided PackageURL is not valid.",
#         "purl": "pkg:pypi/@dejacode"
#     },
#     {
#         "valid": true,
#         "exists": false,
#         "message": "The provided PackageURL is valid, but does not exist in the upstream repo.",
#         "purl": "pkg:pypi/dejacode@12345"
#     },
#     {
#         "valid": true,
#         "exists": true,
#         "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
#         "purl": "pkg:cargo/rand@0.7.2"
#     },
#     {
#         "valid": true,
#         "exists": null,
#         "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type.",
#         "purl": "pkg:nginx/nginx@0.8.9?os=windows"
#     }
# ]


# This code and the related tests have not yet been converted to a SCTK-like data structure.
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
# TODO: need to strip versions, qualifiers and subpath data and note that in a warning.
def get_versions(purls, output, file):
    """
    Given one or more PURLs, return a list of all known versions for each PURL.

    Version information is not needed in submitted PURLs and if included will
    be removed before processing.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    command_name = context.command.name

    # purl_versions = list_versions(purls)
    purl_versions = list_versions(purls, output, file, command_name)
    json.dump(purl_versions, output, indent=4)


# def list_versions(purls):
# HEY: 2024-02-07 Wednesday 18:23:54.  Though we're now passing data needed for construct_headers(), construct_headers() has not yet been implemented for this `versions` command -- or for the `validate` command either.
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

        # TODO: Add to warnings when we restructure to SCTK-like structure.
        # if check_versions_purl(purl):
        #     print(check_versions_purl(purl))
        #     continue

        # # TODO: The `for` statement throws `TypeError: 'NoneType' object is not iterable` if, e.g., the PURL is missing `/debian/` -- `pkg:deb/debian/2ping` succeeds while `pkg:deb/2ping` throws that TypeError.
        # # TODO: So let's define it first as a variable so we can catch with a try/except.  Need to add it as a warning, too.
        # # HEY: In place of a return, we want somehow to pass this as a `warning` in the `header` -- this has not yet been converted to the SCTK-like data structure -- and then we want a `continue`
        # # versions() calls /home/jmh/dev/nexb/purldb/venv/lib/python3.8/site-packages/fetchcode/package_versions.py
        # if versions(purl) is None:
        #     # print(f"\n\nNone None None None None")
        #     print(
        #         f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
        #     )
        #     # TODO: Add as a warning to headers
        #     continue

        if command_name == "versions" and check_versions_purl(purl) == "not_valid":
            print(
                f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if (
            command_name == "versions"
            and check_versions_purl(purl) == "valid_but_not_supported"
        ):
            print(
                f"The provided PackageURL '{purl}' is valid, but `versions` does not support this package type."
            )
            continue

        if (
            command_name == "versions"
            and check_versions_purl(purl) == "failed_to_fetch"
        ):
            print(
                f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
            )
            continue

        # else:
        #     # print(f"\n\nOh oh ....")

        #     # try:
        #     #     list_purl_versions = list(versions(purl))
        #     # except TypeError as error:
        #     #     print(
        #     #         f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
        #     #     )
        #     #     continue

        for package_version_object in list(versions(purl)):
            # for package_version_object in list_purl_versions:
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
    """
    results = check_existence(purl)

    if results["valid"] == False:
        # return f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."
        return "not_valid"

    supported = SUPPORTED_ECOSYSTEMS

    versions_purl = PackageURL.from_string(purl)

    if versions_purl.type not in supported:
        # return f"The provided PackageURL '{purl}' is valid, but `versions` is not supported for this package type."
        return "valid_but_not_supported"

    # # TODO 2024-02-05 Monday 16:29:23.  I originally used this if test and message in `meta` but found today that it blocks the desired return of data on `pkg:rubygems/bundler-sass` and commented it out -- to be deleted when I'm certain.  Same with `urls` -- commented out, to be deleted.  Do we want this here?
    # # HEY: 2024-02-05 Monday 16:44:21.  This is triggered by running `versions` on 'pkg:pypi/dejacode@55.0.0' or 'pkg:pypi/matchcode', neither of which exists -- so we'll keep this here.
    # # 2024-02-05 Monday 19:02:34.  We'll also add it above in the try/catch because fetchcode/package_versions.py throws an error
    # if results["exists"] != True:
    #     return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."

    # YO: 2024-02-07 Wednesday 13:17:57.  Revisit this after my break.  `urls` has this entirely commented out, while `meta` has this:
    if results["exists"] == False:
        #     return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
        return "failed_to_fetch"


def check_for_duplicate_input_sources(purls, file):
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")


if __name__ == "__main__":
    purlcli()
