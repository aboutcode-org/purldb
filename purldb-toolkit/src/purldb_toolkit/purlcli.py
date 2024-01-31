import json
from importlib.metadata import version

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS, versions
from packageurl import PackageURL
from packageurl.contrib import purl2url


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
    help="Write versions output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
def get_meta(purls, output, file):
    """
    Given one or more PURLs, for each PURL, return a mapping of metadata
    fetched from the fetchcode package.py info() function.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    context = click.get_current_context()
    manual_command_name = context.command.name

    meta_info = get_meta_details(purls, output, file, manual_command_name)
    json.dump(meta_info, output, indent=4)


def get_meta_details(purls, output, file, manual_command_name):
    """
    Return a dictionary containing metadata for each PURL in the `purls` input
    list.  `check_meta_purl()` will print an error message to the console
    (also displayed in the JSON output) when necessary.
    """
    context_purls = [p for p in purls]
    context_file = file
    context_file_value = None
    if context_file:
        context_file_value = context_file.name

    meta_details = {}
    meta_details["headers"] = []
    meta_details["packages"] = []

    headers_content = {}
    options = {}

    errors = []
    warnings = []

    # TODO: How do we want to implement the try/except, the results of which will be reported in the JSON output?

    headers_content["tool_name"] = "purlcli"
    headers_content["tool_version"] = version("purldb_toolkit")

    options["command"] = manual_command_name
    options["--purl"] = context_purls
    options["--file"] = context_file_value

    if isinstance(output, str):
        options["--output"] = output
    else:
        options["--output"] = output.name

    headers_content["options"] = options
    headers_content["purls"] = purls

    meta_details["headers"].append(headers_content)

    for purl in purls:
        meta_detail = {}
        meta_detail["purl"] = purl
        meta_detail["metadata"] = []

        purl = purl.strip()
        if not purl:
            continue

        if check_meta_purl(purl):
            print(check_meta_purl(purl))
            warnings.append(check_meta_purl(purl))
            continue

        for release in list(info(purl)):
            release_detail = release.to_dict()
            release_detail.move_to_end("purl", last=False)
            meta_details["packages"].append(release_detail)

    headers_content["errors"] = errors
    headers_content["warnings"] = warnings

    return meta_details


def check_meta_purl(purl):
    """
    Return a message for printing to the console if the input PURL is invalid,
    its type is not supported by `meta` or its existence was not validated.
    This message will also be reported in the `warnings` field of the `header`
    section of the JSON object returned by the `meta` command.
    """
    results = check_existence(purl)

    if results["valid"] == False:
        return f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."

    # This is manually constructed from a visual inspection of fetchcode/package.py:
    SUPPORTED_ECOSYSTEMS = [
        "cargo",
        "npm",
        "pypi",
        "github",
        "bitbucket",
        "rubygems",
    ]
    meta_purl = PackageURL.from_string(purl)

    if meta_purl.type not in SUPPORTED_ECOSYSTEMS:
        return f"The provided PackageURL '{purl}' is valid, but `meta` is not supported for this package type."

    if results["exists"] != True:
        return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."


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
    help="Write versions output as JSON to FILE.",
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
    fetched from packageurl-python purl2url.py file.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    purl_urls = get_url_details(purls, head)
    json.dump(purl_urls, output, indent=4)


def get_url_details(purls, head):
    """
    Return a dictionary containing URLs for each PURL in the `purls` input list.
    """
    url_sctk = {}
    url_sctk["headers"] = []
    url_sctk["packages"] = []

    url_headers = {}
    url_headers["tool_name"] = "to come"
    url_headers["tool_version"] = "to come"

    url_options = {}
    url_options["command"] = "to come"

    url_headers["options"] = url_options
    url_sctk["headers"].append(url_headers)

    url_purls = []

    for purl in purls:
        url_detail = {}
        url_detail["purl"] = purl

        urls = []
        url_detail["url_type"] = urls

        purl_urls = {}

        purl = purl.strip()
        if not purl:
            continue

        # TODO: Need to refactor the names -- too many combos now of `*url*` and `*purl*`.  ;-)

        # TODO: validate, i.e., check_existence(purl).
        # check_url_purl

        # TODO: make a head request to validate the existence of each URL.
        # if head:
        #     make_head_request(url_detail)

        # url_sctk = {}
        # url_sctk["headers"] = []
        # url_sctk["packages"] = []

        # url_headers = {}
        # url_headers["tool_name"] = "to come"
        # url_headers["tool_version"] = "to come"

        # url_options = {}
        # url_options["command"] = "to come"
        # url_purls = []
        url_purls.append(purl)
        url_options["--purl"] = url_purls

        # url_headers["options"] = url_options
        # url_sctk["headers"].append(url_headers)

        url_packages = {}
        url_packages["purl"] = purl

        # ZZZ: add url indo to this list -- but create the list first and add to that, then that list to
        # url_packages["urls"] = []

        url_sctk["packages"].append(url_packages)

        # print(f"\nurl_sctk = {url_sctk}")

        # ---------------------------------------------------------------------

        # download_url = {"download_url": purl2url.get_download_url(purl)}
        # # print(f"\ndownload_url = {download_url}")
        # # urls["download_url"] = download_url
        # urls.append(download_url)
        purl_urls["download_url"] = purl2url.get_download_url(purl)
        # urls.append(purl_urls)
        # urls.append({"url": "download_url", "http_status_code": "TO COME"})
        nested_dict = {}
        nested_dict["download_url"] = purl2url.get_download_url(purl)
        nested_dict["http_status_code"] = "TO COME"
        # nested_dict["abc"] = "TO COME"
        urls.append(nested_dict)

        # inferred_urls = {"inferred_urls": purl2url.get_inferred_urls(purl)}
        # # print(f"\ninferred_urls = {inferred_urls}")
        # # urls["inferred_urls"] = inferred_urls
        # urls.append(inferred_urls)
        purl_urls["inferred_urls"] = purl2url.get_inferred_urls(purl)

        # repo_download_url = {"repo_download_url": purl2url.get_repo_download_url(purl)}
        # # print(f"\nrepo_download_url = {repo_download_url}")
        # # urls["repo_download_url"] = repo_download_url
        # urls.append(repo_download_url)
        purl_urls["repo_download_url"] = purl2url.get_repo_download_url(purl)

        url_purl = PackageURL.from_string(purl)
        # repo_download_url_by_package_type = {
        #     "repo_download_url_by_package_type": (
        #         purl2url.get_repo_download_url_by_package_type(
        #             url_purl.type, url_purl.namespace, url_purl.name, url_purl.version
        #         )
        #     )
        # }
        # # print(
        # #     f"\nrepo_download_url_by_package_type = {repo_download_url_by_package_type}"
        # # )
        # # urls["repo_download_url_by_package_type"] = repo_download_url_by_package_type
        # urls.append(repo_download_url_by_package_type)
        purl_urls[
            "repo_download_url_by_package_type"
        ] = purl2url.get_repo_download_url_by_package_type(
            url_purl.type, url_purl.namespace, url_purl.name, url_purl.version
        )

        # repo_url = {"repo_url": purl2url.get_repo_url(purl)}
        # # print(f"\nrepo_url = {repo_url}")
        # # url_detail["urls"].append(repo_url)
        # # urls["repo_url"] = repo_url
        # urls.append(repo_url)
        purl_urls["repo_url"] = purl2url.get_repo_url(purl)

        # url = {"url": purl2url.get_url(purl)}
        # # print(f"\nurl = {url}")
        # # urls["url"] = url
        # urls.append(url)
        purl_urls["url"] = purl2url.get_url(purl)

        # 2024-01-25 Thursday 18:30:36.  Let's test my new purl2url function that I've added to the newly-forked packageurl-python repo: `print_hello()`.  It works.  Excellent.
        # test_print = purl2url.print_hello(purl)

        # 2024-01-29 Monday 18:47:19.  ========================================
        download_data = {}
        download_data["url"] = purl2url.get_download_url(purl)
        if head:
            download_data["http_status_code"] = "COMING SOON"
        url_packages["download_url"] = download_data

        inferred_urls_data = {}
        # download_data["url"] = purl2url.get_download_url(purl)
        # if head:
        #     download_data["http_status_code"] = "COMING SOON"
        # url_packages["download_url"] = download_data

        repo_download_data = {}
        repo_download_data["repo_download_url"] = purl2url.get_repo_download_url(purl)
        if head:
            repo_download_data["http_status_code"] = "COMING SOON"
        url_packages["repo_download_url"] = repo_download_data

        # ALERT 2024-01-29 Monday 19:12:50.  This failed.  Why?
        repo_download_url_by_package_type_data = {}
        # repo_download_url_by_package_type_data[
        #     "url"
        # ] = purl2url.get_repo_download_url_by_package_type(purl)
        repo_download_url_by_package_type_data[
            "url"
        ] = purl2url.get_repo_download_url_by_package_type(
            url_purl.type, url_purl.namespace, url_purl.name, url_purl.version
        )
        if head:
            repo_download_url_by_package_type_data["http_status_code"] = "COMING SOON"
        url_packages[
            "repo_download_url_by_package_type"
        ] = repo_download_url_by_package_type_data

        repo_url_data = {}
        repo_url_data["url"] = purl2url.get_repo_url(purl)
        if head:
            download_data["http_status_code"] = "COMING SOON"
        url_packages["repo_url"] = repo_url_data

        url_data = {}
        url_data["url"] = purl2url.get_url(purl)
        if head:
            url_data["http_status_code"] = "COMING SOON"
        url_packages["url"] = url_data
        # =====================================================================

        urls.append(purl_urls)

        # YO: 2024-01-29 Monday 15:17:51.  Way down here, we append the url detail to the new sctk-structured list --
        # 2024-01-29 Monday 20:58:54.  And now that we've constructed the new approach, not nested under 'urls', we don't want this anymore.
        # url_packages["urls"] = urls

        # 2024-01-29 Monday 18:40:17.  No longer used
        # url_details.append(url_detail)

    # print(f"\n==========================================================")
    # print(json.dumps(url_sctk, indent=4, sort_keys=False))
    # print(f"==========================================================\n")

    # return url_details
    # 2024-01-29 Monday 16:27:11.  No, we now want to return `url_sctk`
    return url_sctk


def make_head_request(url_detail):
    """
    Make a head request and return a message containing data regarding the
    status of each of the input PURL's URLs.
    """
    # print(f'\n"make_head_request()" is coming soon ....')
    print(f"\nurl_detail = {url_detail}")
    print()

    head_request = {}

    for k, v in url_detail["url_type"][0].items():
        if v is None:
            print(f"\nk = {k}")
            head_request[k] = "N/A"
        else:
            # head_request[k] = "some value"
            if k == "inferred_urls":
                inferred_head_request = []
                for inferred_url in v:
                    head_response = requests.head(inferred_url)
                    inferred_head_request.append(head_response)
                    # print(f"\nhead_response = {head_response}")
                    print(f"\nhead_response.status_code = {head_response.status_code}")
                    # print(f"\nhead_response.headers = {head_response.headers}")
                    print()
                    for entry in head_response.headers:
                        print(f"{entry} = {head_response.headers[entry]}")
                head_request[k] = inferred_head_request
            else:
                head_response = requests.head(v)
                # head_request[k] = "some value"
                head_request[k] = head_response
                # print(f"\nhead_response = {head_response}")
                print(f"\nhead_response.status_code = {head_response.status_code}")
                # print(f"\nhead_response.headers = {head_response.headers}")

    print(f"\nhead_request = {head_request}")
    # print(f"\nhead_request = {json.dumps(head_request, indent=4, sort_keys=False)}")
    # print(json.dumps(head_request, indent=4, sort_keys=False))
    print()


def check_url_purl(purl):
    """
    Return a message for printing to the console if the input PURL is invalid,
    its type is not supported by `meta` or its existence was not validated.
    """
    results = check_existence(purl)

    if results["valid"] == False:
        return f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."

    # This list (1) is manually constructed from a visual inspection of packageurl-python/src/packageurl/contrib/purl2url.py and (2) applies to the purl2url.py `repo_url`:
    SUPPORTED_ECOSYSTEMS = [
        "bitbucket",
        "cargo",
        "github",
        "gitlab",
        "golang",
        "hackage",
        "npm",
        "nuget",
        "pypi",
        "rubygems",
    ]
    meta_purl = PackageURL.from_string(purl)

    if meta_purl.type not in SUPPORTED_ECOSYSTEMS:
        return f"The provided PackageURL '{purl}' is valid, but `urls` is not supported for this package type."

    if meta_purl.type in SUPPORTED_ECOSYSTEMS and meta_purl.type == any(
        "golang", "pypi"
    ):
        return f"The provided PackageURL '{purl}' is valid, but `urls` is not fully supported for this package type."

    if results["exists"] != True:
        return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."

    # This applies to the purl2url.py `download_url` (as of 2024-01-30 Tuesday 09:46:16, it's the same as the `repo_url` list above EXCEPT it does not include `golang` or `pypi`):
    # SUPPORTED_ECOSYSTEMS = [
    #     "bitbucket",
    #     "cargo",
    #     "github",
    #     "gitlab",
    #     "hackage",
    #     "npm",
    #     "nuget",
    #     "rubygems",
    # ]


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

    return validated_purls


def check_existence(purl):
    """
    Return a JSON object containing data regarding the validity of the input PURL.
    """
    api_query = "https://public.purldb.io/api/validate/"
    purl = purl.strip()
    request_body = {"purl": purl, "check_existence": True}
    response = requests.get(api_query, params=request_body)
    results = response.json()

    return results


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
def get_versions(purls, output, file):
    """
    Given one or more PURLs, return a list of all known versions for each PURL.
    """
    check_for_duplicate_input_sources(purls, file)

    if file:
        purls = file.read().splitlines(False)

    purl_versions = list_versions(purls)
    json.dump(purl_versions, output, indent=4)


def list_versions(purls):
    """
    Return a list of dictionaries containing version-related data for each PURL
    in the `purls` input list.  `check_versions_purl()` will print an error
    message to the console when necessary.
    """
    purl_versions = []
    for purl in purls:
        purl_data = {}
        purl_data["purl"] = purl
        purl_data["versions"] = []

        purl = purl.strip()
        if not purl:
            continue

        if check_versions_purl(purl):
            print(check_versions_purl(purl))
            continue

        for package_version_object in list(versions(purl)):
            purl_version_data = {}
            purl_version = package_version_object.to_dict()["value"]
            nested_purl = purl + "@" + f"{purl_version}"

            purl_version_data["purl"] = nested_purl
            purl_version_data["version"] = f"{purl_version}"
            purl_version_data[
                "release_date"
            ] = f'{package_version_object.to_dict()["release_date"]}'

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
        return f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."

    supported = SUPPORTED_ECOSYSTEMS

    versions_purl = PackageURL.from_string(purl)

    if versions_purl.type not in supported:
        return f"The provided PackageURL '{purl}' is valid, but `versions` is not supported for this package type."

    if results["exists"] != True:
        return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."


def check_for_duplicate_input_sources(purls, file):
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")


if __name__ == "__main__":
    purlcli()
