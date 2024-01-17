import json

import click
import requests
from fetchcode.package import info
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS, versions


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
    purl_versions = []
    for purl in purls:
        dict_output = {}
        dict_output["purl"] = purl
        dict_output["versions"] = []

        purl = purl.strip()
        if not purl:
            continue

        if check_versions_purl(purl):
            print(check_versions_purl(purl))
            continue

        for package_version_object in list(versions(purl)):
            nested_dict = {}
            nested_purl = purl + "@" + f'{package_version_object.to_dict()["value"]}'

            nested_dict["purl"] = nested_purl
            nested_dict["version"] = f'{package_version_object.to_dict()["value"]}'
            nested_dict[
                "release_date"
            ] = f'{package_version_object.to_dict()["release_date"]}'

            dict_output["versions"].append(nested_dict)

        purl_versions.append(dict_output)

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
    meta_details = []
    purl_versions = []

    for purl in purls:
        dict_output = {}
        dict_output["purl"] = purl
        dict_output["metadata"] = []

        purl = purl.strip()
        if not purl:
            continue

        if check_meta_purl(purl):
            print(check_meta_purl(purl))
            continue

        releases = []
        for release in list(info(purl)):
            dict_output["metadata"].append(release.to_dict())

        purl_versions.append(dict_output)

    return purl_versions


def check_existence(purl):
    api_query = "https://public.purldb.io/api/validate/"
    purl = purl.strip()
    request_body = {"purl": purl, "check_existence": True}
    response = requests.get(api_query, params=request_body)
    results = response.json()

    return results


def check_versions_purl(purl):
    results = check_existence(purl)

    if results["valid"] == False:
        return f"There was an error with your '{purl}' query -- the Package URL you provided is not valid."

    supported = SUPPORTED_ECOSYSTEMS

    purl_type = purl.split(":")[1].split("/")[0]

    if purl_type not in supported:
        return f"The provided PackageURL '{purl}' is valid, but `versions` is not supported for this package type."

    if results["exists"] != True:
        return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."


def check_meta_purl(purl):
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
    purl_type = purl.split(":")[1].split("/")[0]
    if purl_type not in SUPPORTED_ECOSYSTEMS:
        return f"The provided PackageURL '{purl}' is valid, but `meta` is not supported for this package type."

    if results["exists"] != True:
        return f"There was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."


if __name__ == "__main__":
    purlcli()
