import json

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS, versions
from packageurl import PackageURL


@click.group()
def purlcli():
    """
    Return information from a PURL.
    """


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
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")

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
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")

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
    Given one or more PURLs, return a mapping of metadata fetched from the API for each PURL.
    """
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")

    if file:
        purls = file.read().splitlines(False)

    meta_info = get_meta_details(purls)
    json.dump(meta_info, output, indent=4)


def get_meta_details(purls):
    """
    Return a list of dictionaries containing metadata for each PURL
    in the `purls` input list.  `check_meta_purl()` will print an error
    message to the console when necessary.
    """
    meta_details = []

    for purl in purls:
        meta_detail = {}
        meta_detail["purl"] = purl
        meta_detail["metadata"] = []

        purl = purl.strip()
        if not purl:
            continue

        if check_meta_purl(purl):
            print(check_meta_purl(purl))
            continue

        releases = []
        for release in list(info(purl)):
            meta_detail["metadata"].append(release.to_dict())

        meta_details.append(meta_detail)

    return meta_details


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


def check_meta_purl(purl):
    """
    Return a message for printing to the console if the input PURL is invalid,
    its type is not supported by `meta` or its existence was not validated.
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


if __name__ == "__main__":
    purlcli()
