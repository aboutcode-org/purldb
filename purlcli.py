import json

import click
import requests
from fetchcode.package_versions import PackageVersion, router, versions


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
    packageversion_objects = []

    purl_versions = []
    list_of_dict_output_json_dumps = []
    for purl in purls:
        dict_output = {}
        dict_output["purl"] = purl
        dict_output["versions"] = []

        purl = purl.strip()
        if not purl:
            continue

        api_query = "https://public.purldb.io/api/validate/"
        purl = purl.strip()
        request_body = {"purl": purl, "check_existence": True}
        response = requests.get(api_query, params=request_body)
        results = response.json()

        if results["valid"] == False:
            print(
                f"\nThere was an error with your '{purl}' query -- the Package URL you provided is not valid."
            )
            continue

        if results["exists"] != True:
            print(
                f"\nThere was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
            )
            continue

        # results = list(router.process(purl))
        # results_versions = list(versions(purl))
        # packageversion_objects.append(results)
        # results_values = [v.value for v in router.process(purl)]

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

        # dict_output_json_dumps = json.dumps(dict_output, indent=2, sort_keys=False)
        # list_of_dict_output_json_dumps.append(dict_output_json_dumps)

    return purl_versions


if __name__ == "__main__":
    purlcli()
