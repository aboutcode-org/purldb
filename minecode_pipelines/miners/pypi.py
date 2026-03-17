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
Visitors for Pypi and Pypi-like Python package repositories.

We have this hierarchy in Pypi simple/ index:
    pypi projects (JSON/HTML) -> project versions (JSON/HTML) -> download urls

https://pypi.org/simple/
Pypi serves a main index via JSON/HTML API that contains a list of package names
and some info on when a package was updated by releasing a new version.
See https://docs.pypi.org/api/index-api/ for more details.
This index also has a list of versions and download URLs of all
uploaded/available package archives and some basic metadata.

https://pypi.org/pypi/{name}/json
For each package, a JSON contains details including the list of all releases
and archives, their URLs, and some metadata for each release.
For each release, a JSON contains details for the released version and all the
downloads available for this release.
"""


pypi_json_headers = {"Accept": "application/vnd.pypi.simple.v1+json"}


PYPI_SIMPLE_REPO = "https://pypi.org/simple"
PYPI_METADATA_REPO = "https://pypi.org/pypi"
PYPI_TYPE = "pypi"


def get_pypi_packages(pypi_repo, logger=None):
    response = requests.get(pypi_repo, headers=pypi_json_headers)
    if not response.ok:
        return

    return response.json()


def get_pypi_package_versions(name):
    versions = []

    project_index_api_url = PYPI_SIMPLE_REPO + "/" + name
    response = requests.get(project_index_api_url, headers=pypi_json_headers)
    if not response.ok:
        return versions

    project_data = response.json()
    versions = project_data.get("versions", [])
    return versions


def get_pypi_packageurls(name):
    packageurls = []

    for version in get_pypi_package_versions(name=name):
        purl = PackageURL(
            type=PYPI_TYPE,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls


def get_pypi_package_data(name):
    package_data_by_purl = {}

    for purl in get_pypi_packageurls(name):
        package_data_url = PYPI_METADATA_REPO + "/" + name + "/" + purl.version
        response = requests.get(package_data_url, headers=pypi_json_headers)
        if not response.ok:
            continue
        package_data_by_purl[purl.to_string()] = response.json()

    return package_data_by_purl


def load_pypi_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    last_serial = packages_data.get("meta").get("_last-serial")
    packages = packages_data.get("projects")

    return last_serial, packages


def get_last_serial_from_packages(packages_file):
    with open(packages_file) as f:
        packages_data = json.load(f)

    last_serial = packages_data.get("meta").get("_last-serial")
    return last_serial
