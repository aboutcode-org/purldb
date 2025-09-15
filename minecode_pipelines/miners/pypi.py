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

from minecode_pipelines.utils import get_temp_file
from minecode_pipelines.pipes import write_data_to_json_file

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


PYPI_REPO = "https://pypi.org/simple/"
PYPI_TYPE = "pypi"


def get_pypi_packages(pypi_repo, logger=None):
    response = requests.get(pypi_repo, headers=pypi_json_headers)
    if not response.ok:
        return

    return response.json()


def write_packages_json(packages, name):
    temp_file = get_temp_file(name)
    write_data_to_json_file(path=temp_file, data=packages)
    return temp_file


def get_pypi_packageurls(name):
    packageurls = []

    project_index_api_url = PYPI_REPO + name
    response = requests.get(project_index_api_url, headers=pypi_json_headers)
    if not response.ok:
        return packageurls

    project_data = response.json()
    for version in project_data.get("versions"):
        purl = PackageURL(
            type=PYPI_TYPE,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls


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
