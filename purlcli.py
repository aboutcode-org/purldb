"""
2024-01-09 Tuesday 11:59:11.  This began the day as a cleaned-up version of purlcli-03.py.
"""

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
    help="Write validation output as JSON to FILE.",
)
@click.option(
    "--file",
    type=click.File(mode="r", encoding="utf-8"),
    required=False,
    help="Read a list of PURLs from a FILE, one per line.",
)
def get_versions(purls, output, file):
    """
    Check the syntax of one or more PURLs.
    """
    # if (purls and file) or not (purls or file):
    #     raise click.UsageError("Use either purls or file but not both.")
    if purls and file:
        raise click.UsageError("Use either purls or file but not both.")

    if not (purls or file):
        raise click.UsageError("Use either purls or file.")

    if file:
        purls = file.read().splitlines(False)

    purl_versions = list_versions(purls)

    purl_versions
    # print(f"\nlen(purl_versions) = {len(purl_versions)}")


def list_versions(purls):
    # print(f"\nlen(purls) = {len(purls)}")
    # print(f"\ntype(purls) = {type(purls)}")
    # print(f"\npurls = {purls}")
    purl_versions = []

    list_of_dict_outputs = []
    # and this will hold the dict_outputs converted with json.dumps():
    list_of_dict_output_json_dumps = []
    for purl in purls:
        dict_output = {}
        # print(f"purl = {purl}")
        dict_output["purl"] = purl
        dict_output["versions"] = []
        # YO: Do we want to check for version data and if found remove it?  Or allow?
        purl = purl.strip()
        if not purl:
            continue

        # YO: try/except -- 2024-01-07 Sunday 21:14:37.  I tried this but the error thrown by fetchcode does not trigger the try/except.
        # https://github.com/nexB/fetchcode/blob/d0a3fa9bb56dc3a77f7d3d7bd5b8d0e40c7a8612/src/fetchcode/package_versions.py#L512-L524
        # try:
        #     some_variable = list(router.process(purl))

        # 2024-01-07 Sunday 21:58:44.  TEST to detect fetchcode error.
        # result = os.system("python other_script.py")
        # if 0 == result:
        # YO: 2024-01-07 Sunday 22:25:38.  This DOES catch an error -- empty list means that, for some unidentified reason, there is no responsive data.
        # results = list(router.process(purl))
        # if results != []:
        #     print(" Command executed successfully")
        #     print(f"results = {results}")
        # else:
        #     print(" Command didn't execute successfully")
        #     print(f"results = {results}")

        # 2024-01-08 Monday 15:28:11.  Can this alert us to a problem w/o that pseudo error message?
        # test_variable01 = list(router.process(purl))
        # print(f"\ntest_variable01 = {test_variable01}")

        # YO: 2024-01-08 Monday 15:25:28.  Each of these throws a pseudo error for pkg:pypi/ogdendunes but not for pkg:pypi/foobar -- Error while fetching 'https://pypi.org/pypi/ogdendunes/json': 404 -- but each produces an empty [].
        # results = list(versions(purl))
        # results = list(versions(purl))
        # results = list(router.process(purl))

        # test01 = versions(purl)
        # test02 = router.process(purl)
        # print(f"results = {results}")
        # print(f"test01 = {test01}")
        # print(f"test02 = {test02}")
        # ZAP: If we have multiple inputs and some are valid, I assume we DO want to return data for those.
        # if results == []:
        #     print(
        #         f"\nThere was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
        #     )
        #     continue

        # ZAP: 2024-01-08 Monday 17:07:34.  Rather than test results as above, we'll use 'validate'.

        api_query = "https://public.purldb.io/api/validate/"
        purl = purl.strip()
        request_body = {"purl": purl, "check_existence": True}
        response = requests.get(api_query, params=request_body)
        results = response.json()

        # print(f"\n\nresults = {results}")

        if results["exists"] != True:
            print(
                f"\nThere was an error with your '{purl}' query.  Make sure that '{purl}' actually exists in the relevant repository."
            )
            continue

        # This works: this is a list of PackageVersion objects
        # print(f"\n\n* ABOUT TO PROCESS A PURL")
        results = list(router.process(purl))
        # print(f"* JUST PROCESSED A PURL")

        # print(f"\n\nrouter.process(purl) = {router.process(purl)}")

        # print(f"\n\n* ABOUT TO PROCESS A PURL")
        # print(f"\nlist(router.process(purl)) = {list(router.process(purl))}")
        # print(f"* JUST PROCESSED A PURL")

        # versions(purl) is a generator object
        # print(f"\nversions(purl) = {versions(purl)}")

        # Another test -- this is a list of PackageVersion objects
        # print(f"\n\n* ABOUT TO PROCESS A PURL")
        results_versions = list(versions(purl))
        # print(f"* JUST PROCESSED A PURL")
        # print(f"\nresults_versions = {results_versions}")

        purl_versions.append(results)

        # Test: list of strings
        # print(f"\n\n* ABOUT TO PROCESS A PURL")
        results_values = [v.value for v in router.process(purl)]
        # print(f"* JUST PROCESSED A PURL")
        # print(f"\nresults_values = {results_values}")

        # 2024-01-05 Friday 17:25:41.  Iterate through PackageVersion() objects
        # YO: rename the variable!
        # print(f"\n\n* ABOUT TO PROCESS A PURL")
        for package_version_object in list(versions(purl)):
            # YO This print statement is not reached when the PURL query returns a 404.
            # print(f"* JUST PROCESSED A PURL")
            # print(f"\n*** package_version_object = {package_version_object}")

            # print(
            #     f"\n*** package_version_object.to_dict() = {package_version_object.to_dict()}"
            # )

            # print(
            #     f"\n*** package_version_object.to_dict()['value'] = {package_version_object.to_dict()['value']}"
            # )

            # print(
            #     f"\n*** package_version_object.to_dict()['release_date'] = {package_version_object.to_dict()['release_date']}"
            # )

            # Here, too, create dict which we'll convert to JSON with json.dumps().
            nested_dict = {}
            # print(f"type(nested_dict) = {type(nested_dict)}")

            nested_purl = purl + "@" + f'{package_version_object.to_dict()["value"]}'
            # nested_purl = "TEST"

            # dict_output["versions"].append({"purl": nested_purl})
            nested_dict["purl"] = nested_purl
            nested_dict["version"] = f'{package_version_object.to_dict()["value"]}'
            nested_dict[
                "release_date"
            ] = f'{package_version_object.to_dict()["release_date"]}'
            dict_output["versions"].append(nested_dict)
            # # print(f"\nnested_dict = {nested_dict}")
            # print(
            #     f"\nnested_dict = {json.dumps(nested_dict, indent=4, sort_keys=False)}"
            # )

        # dict
        # print(f"\n==> dict_output = {dict_output}")
        # print(f"\n==> type(dict_output) = {type(dict_output)}")
        # add to list
        list_of_dict_outputs.append(dict_output)
        # 2024-01-05 Friday 20:53:18.  Does this format?
        # list_of_dict_outputs.append(json.dumps(dict_output, indent=2, sort_keys=False))

        # 2024-01-05 Friday 18:31:54.  Let's convert dict_output with json.loads() and json.dumps() -- but that errors.  Omit json.loads()???
        # json.dumps() works but the .json file is not formatted, i.e., no indents
        dict_output_json_dumps = json.dumps(dict_output, indent=2, sort_keys=False)

        # no the next 2 fail.
        # dict_output_json_loads = json.loads(dict_output)
        # dict_output_json_dumps = json.dumps(
        #     dict_output_json_loads, indent=2, sort_keys=False
        # )

        # YO: 2024-01-08 Monday 15:13:07.  This is a list of the versions -- each nested_dict -- above.
        # print(f"\n==> dict_output_json_dumps = {dict_output_json_dumps}")
        # and add to the separate list
        list_of_dict_output_json_dumps.append(dict_output_json_dumps)

    # ZAP: 2024-01-08 Monday 13:37:29.  We don't want these to rpint for a PURL that threw an error, so need to revise.
    # print(f"\npurl_versions = {purl_versions}")
    # print(f"\n==> list_of_dict_outputs = {list_of_dict_outputs}")
    # print(f"\n==> list_of_dict_output_json_dumps = {list_of_dict_output_json_dumps}")

    with open(
        "/mnt/c/nexb/purldb-testing/2024-01-08-testing/json-output/purlcli-03-list_of_dict_outputs-2024-01-08.json",
        "w",
    ) as f:
        json.dump(list_of_dict_outputs, f)

    with open(
        "/mnt/c/nexb/purldb-testing/2024-01-08-testing/json-output/purlcli-03-list_of_dict_output_json_dumps-2024-01-08.json",
        "w",
    ) as f:
        json.dump(list_of_dict_output_json_dumps, f)

    with open(
        "/mnt/c/nexb/purldb-testing/2024-01-08-testing/json-output/purlcli-03-formatted_list_of_dict_output_json_dumps-2024-01-08.json",
        "w",
    ) as f:
        # json.dump(dict_output_json_dumps, f)
        # json.dump(dict_output_json_dumps, f, indent=4)
        # json.dump(list_of_dict_outputs, f)

        # 2024-01-05 Friday 20:54:27.  This creates formatted JSON in the output file -- not in a list
        # json.dump(dict_output, f, indent=4)

        # json.dump(list_of_dict_outputs, f, indent=4)

        # json.dump([obj for obj in list_of_dict_outputs], f)

        # 2024-01-05 Friday 21:11:21.  THIS NOW WORKS!  OUTPUT IS A LIST OF FORMATTED JSON OBJECTS!
        json.dump([obj for obj in list_of_dict_outputs], f, indent=4)

    # print(json.dumps(dict_output, indent=4, sort_keys=False))
    # print("===")
    print(
        f"\n\nlist_of_dict_outputs = {json.dumps(list_of_dict_outputs, indent=4, sort_keys=False)}"
    )

    return purl_versions


if __name__ == "__main__":
    purlcli()
