#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import json
import requests

from packageurl import PackageURL


"""
Visitors for Npmjs and npmjs-like javascript package repositories.

We have this hierarchy in npm replicate and registry index:
    npm projects replicate.npmjs.com (paginated JSON) -> versions at registry.npmjs.org (JSON) -> download urls

See https://github.com/orgs/community/discussions/152515 for information on
the latest replicate.npmjs.com API.

https://replicate.npmjs.com/_all_docs
This NPMJS replicate API serves as an index to get all npm packages and their revision IDs
in paginated queries.

https://replicate.npmjs.com/_changes
This NPMJS replicate API serves as a CHANGELOG of npm packages with update sequneces which
can be fetched in paginated queries.

https://registry.npmjs.org/{namespace/name}
For each npm package, a JSON containing details including the list of all releases
and archives, their URLs, and some metadata for each release.

https://registry.npmjs.org/{namespace/name}/{version}
For each release, a JSON contains details for the released version and all the
downloads available for this release.
"""


NPM_REPLICATE_REPO = "https://replicate.npmjs.com/"
NPM_REGISTRY_REPO = "https://registry.npmjs.org/"
NPM_TYPE = "NPM"
NPM_REPLICATE_BATCH_SIZE = 10000


def get_package_names_last_key(package_data):
    names = [package.get("id") for package in package_data.get("rows")]
    last_key = package_data.get("rows")[-1].get("key")
    return names, last_key


def get_package_names_last_seq(package_data):
    names = [package.get("id") for package in package_data.get("results")]
    last_seq = package_data.get("last_seq")
    return names, last_seq


def get_current_last_seq(replicate_url=NPM_REPLICATE_REPO):
    npm_replicate_latest_changes = replicate_url + "_changes?descending=True"
    response = requests.get(npm_replicate_latest_changes)
    if not response.ok:
        return

    package_data = response.json()
    _package_names, last_seq = get_package_names_last_seq(package_data)
    return last_seq


def get_updated_npm_packages(last_seq, replicate_url=NPM_REPLICATE_REPO):
    all_package_names = []
    i = 0

    while True:
        print(f"Processing iteration: {i}: changes after seq: {last_seq}")
        npm_replicate_changes = (
            replicate_url + "_changes?" + f"limit={NPM_REPLICATE_BATCH_SIZE}" + f"&since={last_seq}"
        )
        response = requests.get(npm_replicate_changes)
        if not response.ok:
            return all_package_names

        package_data = response.json()
        package_names, last_seq = get_package_names_last_seq(package_data)
        all_package_names.extend(package_names)

        # We have fetched the last set of changes if True
        if len(package_names) < NPM_REPLICATE_BATCH_SIZE:
            break

        i += 1

    return {"packages": all_package_names}, last_seq


def get_npm_packages(replicate_url=NPM_REPLICATE_REPO):
    all_package_names = []

    npm_replicate_all = replicate_url + "_all_docs?" + f"limit={NPM_REPLICATE_BATCH_SIZE}"
    response = requests.get(npm_replicate_all)
    if not response.ok:
        return all_package_names

    package_data = response.json()
    package_names, last_key = get_package_names_last_key(package_data)
    all_package_names.append(package_names)

    total_rows = package_data.get("total_rows")
    iterations = int(total_rows / NPM_REPLICATE_BATCH_SIZE) + 1

    for i in range(iterations):
        npm_replicate_from_id = npm_replicate_all + f'&start_key="{last_key}"'
        print(f"Processing iteration: {i}: {npm_replicate_from_id}")

        response = requests.get(npm_replicate_from_id)
        if not response.ok:
            raise Exception(npm_replicate_from_id, response.text)

        package_data = response.json()
        package_names, last_key = get_package_names_last_key(package_data)
        all_package_names.append(package_names)

    return {"packages": all_package_names}


def get_npm_packageurls(name, npm_repo=NPM_REGISTRY_REPO):
    packageurls = []

    project_index_api_url = npm_repo + name
    response = requests.get(project_index_api_url)
    if not response.ok:
        return packageurls

    project_data = response.json()
    for version in project_data.get("versions"):
        purl = PackageURL(
            type=NPM_TYPE,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls


def load_npm_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    return packages_data.get("packages", [])
