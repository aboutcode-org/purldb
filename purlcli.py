import json

import click
import requests


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
    if (purls and file) or not (purls or file):
        raise click.UsageError("Use either purls or file but not both.")

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


if __name__ == "__main__":
    purlcli()
