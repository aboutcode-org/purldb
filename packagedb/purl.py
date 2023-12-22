import json
from datetime import datetime

import click
import requests

now = datetime.today().strftime("%Y-%m-%d %a. %#I:%M:%S %p")


@click.command()
@click.option(
    "-pv",
    "--purl_validate",
    metavar="purl_validate",
    multiple=True,
    help="Check whether the syntax of the PURL is valid.  Handles multiple inputs: each PURL must be preceded by the -/-- option name.",
)
@click.option(
    "-pv_txt",
    "--purl_validate_txt",
    metavar="purl_validate_txt",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    required=False,
    help="Check whether the syntax of each of the listed PURLs is valid.  Handles multiple inputs contained in a .txt file: each PURL must be on a separate line.",
)
# ZAP: 2023-12-21 Thursday 16:23:32.  When are these input and output arguments required?  Tied to a flag?
@click.argument(
    "input",
    required=True,
    metavar="INPUT",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True
    ),
)
@click.argument(
    "output",
    required=True,
    metavar="OUTPUT",
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True),
)
@click.option(
    "-dt",
    "--datetime",
    help="Get the current datetime.",
)
def cli(purl_validate, purl_validate_txt, datetime):
    # print(f"\nHello!\n")

    if purl_validate:
        print(f"\npurl_validate = {purl_validate}")
        api_query = "https://public.purldb.io/api/validate/"

        # Create a list to hold the dictionaries that we'll then output in a JSON file
        json_list = []

        for purl in purl_validate:
            print(f"\npurl = {purl}")

            request_body = {
                "purl": purl,
                "check_existence": True,
            }

            response = requests.get(
                api_query,
                params=request_body,
            )

            # abc is a dictionary
            abc = json.loads(response.text)
            print(f"\ntype(abc) = {type(abc)}")

            # print(json.dumps(abc, indent=4, sort_keys=False))
            print(f"\n{json.dumps(abc, indent=4, sort_keys=False)}")

            # 2023-12-21 Thursday 09:09:35.  Create JSON file.
            with open(
                "/mnt/c/nexb/purldb-testing/2023-12-21-testing/json-output/2023-12-21-purl_validate-output-01.json",
                "w",
            ) as f_out:
                json.dump(abc, f_out, indent=4)

            json_list.append(abc)

        # Create another JSON file to hold the list of dictionaries
        with open(
            "/mnt/c/nexb/purldb-testing/2023-12-21-testing/json-output/2023-12-21-purl_validate-output-list-01.json",
            "w",
        ) as f_out:
            json.dump(json_list, f_out, indent=4)

    if purl_validate_txt:
        print(f"\npurl_validate_txt = {purl_validate_txt}")

        with open(purl_validate_txt) as f:
            purls = f.read().splitlines()

        print(f"\npurls = {purls}")

        api_query = "https://public.purldb.io/api/validate/"

        # Create a list to hold the dictionaries that we'll then output in a JSON file
        json_list = []

        for purl in purls:
            print(f"\npurl = {purl}")

            request_body = {
                "purl": purl,
                "check_existence": True,
            }

            response = requests.get(
                api_query,
                params=request_body,
            )

            # abc is a dictionary
            abc = json.loads(response.text)
            print(f"\ntype(abc) = {type(abc)}")

            # print(json.dumps(abc, indent=4, sort_keys=False))
            print(f"\n{json.dumps(abc, indent=4, sort_keys=False)}")

            # 2023-12-21 Thursday 09:09:35.  Create JSON file.
            with open(
                "/mnt/c/nexb/purldb-testing/2023-12-21-testing/json-output/2023-12-21-purl_validate_txt-output-01.json",
                "w",
            ) as f_out:
                json.dump(abc, f_out, indent=4)

            json_list.append(abc)

        # Create another JSON file to hold the list of dictionaries
        with open(
            "/mnt/c/nexb/purldb-testing/2023-12-21-testing/json-output/2023-12-21-purl_validate_txt-output-list-01.json",
            "w",
        ) as f_out:
            json.dump(json_list, f_out, indent=4)

    if datetime:
        print(f"\nCurrent time: {now}\n")
