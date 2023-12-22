from datetime import datetime

import click
import requests

now = datetime.today().strftime("%Y-%m-%d %a. %#I:%M:%S %p")


@click.command()
# @click.argument("location", type=click.Path(exists=True, readable=True))
# @click.argument("destination", type=click.Path(exists=False), required=True)
# @click.argument("api_key", envvar="VCIO_API_KEY")
# def cli(
#     location,
#     destination,
#     api_key,
# ):
@click.option(
    "-pv",
    "--purl_validate",
    multiple=True,
    # is_flag=True,
    # show_default=True,
    # default=False,
    help="Check whether the syntax of the PURL is valid.  Handles multiple inputs: each PURL must be preceded by the -/-- option name.",
)
@click.option(
    "-pv_txt",
    "--purl_validate_txt",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    # multiple=True,
    # is_flag=True,
    # show_default=True,
    # default=False,
    required=False,
    help="Check whether the syntax of each of the listed PURLs is valid.  Handles multiple inputs contained in a .txt file: each PURL must be on a separate line.",
)
@click.option(
    "-dt",
    "--datetime",
    # is_flag=True,
    # show_default=True,
    # default=False,
    help="Get the current datetime.",
)
# This is from the fetch_thirdparty.py example -- let's figure out how it works.
# @click.option(
#     "-r",
#     "--requirements",
#     "requirements_files",
#     type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
#     metavar="REQUIREMENT-FILE",
#     # multiple=True,
#     required=False,
#     help="Path to pip requirements file(s) listing thirdparty packages.",
# )
# def cli(purl_validate, purl_validate_txt, datetime, requirements_files):
def cli(purl_validate, purl_validate_txt, datetime):
    print(f"\nHello!\n")

    if purl_validate:
        print(f"purl_validate = {purl_validate}\n")
        # =====================================================

        # ZAP: 2023-12-18 Monday 09:00:24.  Per Slack comments frm Keshav, these work atm:

        # 1.  Check only the PURL syntax, and not whether the PURL exists in the relevant upstream repo:

        # check_existence is currently limited to

        # api_query = "https://public.purldb.io/api/validate/"

        # request_body = {
        #     "purl": "pkg:nginx/nginx@0.8.9?os=windows",
        # }

        # response = requests.get(
        #     api_query,
        #     params=request_body,
        # )

        # 2.  Check (a) the PURL syntax and (b) whether the PURL exists in the relevant upstream repo:

        # `check_existence` is currently limited to `cargo`, `composer`, `deb`, `gem`, `golang`, `hex`, `maven`, `npm`, `nuget` and `pypi` ecosystems.

        api_query = "https://public.purldb.io/api/validate/"

        for purl in purl_validate:
            print(f"purl = {purl}")
            try:
                request_body = {
                    # "purl": "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
                    "purl": purl,
                    "check_existence": True,
                }

                response = requests.get(
                    api_query,
                    params=request_body,
                )

                # =====================================================

                # print("response.content = {}".format(response.content))
                # print("response.json = {}".format(response.json))

                # print("response.json() = {}".format(response.json()))
                # print("len(response.json()) = {}".format(len(response.json())))

                # if response.json().get("results"):
                #     print(
                #         "len(response.json().get('results')) = {}".format(
                #             len(response.json().get("results"))
                #         )
                #     )
                # else:
                #     print("No 'results'")

                import json

                abc = json.loads(response.text)
                # print("abc = {}".format(abc))

                print(json.dumps(abc, indent=4, sort_keys=False))

            # ZAP: 2023-12-20 Wednesday 08:55:23.  Limit this to type error for unhandled PURL types.
            except:
                print(f"Drat!  It looks like we're not yet able to handle '{purl}'.\n")

    # if requirements_files:
    if purl_validate_txt:
        # print(f"Hurrah!")

        print(f"purl_validate_txt = {purl_validate_txt}")

        with open(purl_validate_txt) as f:
            purls = f.read().splitlines()

        print(f"\npurls = {purls}")

        api_query = "https://public.purldb.io/api/validate/"

        for purl in purls:
            print(f"\npurl = {purl}")
            try:
                request_body = {
                    # "purl": "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.14.0-rc1",
                    # "purl": purl,
                    "purl": purl,
                    "check_existence": True,
                }

                response = requests.get(
                    api_query,
                    params=request_body,
                )

                # =====================================================

                # print("response.content = {}".format(response.content))
                # print("response.json = {}".format(response.json))

                # print("response.json() = {}".format(response.json()))
                # print("len(response.json()) = {}".format(len(response.json())))

                # if response.json().get("results"):
                #     print(
                #         "len(response.json().get('results')) = {}".format(
                #             len(response.json().get("results"))
                #         )
                #     )
                # else:
                #     print("No 'results'")

                import json

                abc = json.loads(response.text)
                # print("abc = {}".format(abc))

                print(json.dumps(abc, indent=4, sort_keys=False))

            except:
                print(f"Drat!  It looks like we're not yet able to handle '{purl}'.\n")

    if datetime:
        print(f"\nCurrent time: {now}\n")
