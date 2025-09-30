#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import gzip
import requests

from bs4 import BeautifulSoup


from packageurl import PackageURL

from minecode_pipelines.utils import get_temp_file
from minecode_pipelines.pipes import write_data_to_json_file

"""
Visitors for cpan and cpan-like perl package repositories.
"""


CPAN_REPO = "https://www.cpan.org/"
CPAN_TYPE = "cpan"


def get_cpan_packages(cpan_repo=CPAN_REPO, logger=None):
    cpan_packages_url = cpan_repo + "modules/02packages.details.txt.gz"
    local_filename = "cpan_packages.gz"

    response = requests.get(cpan_packages_url, stream=True)
    if not response.ok:
        return

    with open(local_filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    with gzip.open("cpan_packages.gz", "rb") as f_in:
        with open("cpan_packages.txt", "wb") as f_out:
            f_out.writelines(f_in)

    with open("cpan_packages.txt", encoding="utf-8") as file:
        packages_content = file.read()

    package_path_by_name = {}

    modules = packages_content.split("\n")[9:-1]
    for module in modules:
        info = [section for section in module.split(" ") if section]
        package_path = info[-1]
        path_segments = package_path.split("/")
        filename = path_segments.pop()
        path_prefix = "/".join(path_segments)

        name_version = filename.replace(".tar.gz", "").split("-")
        _version = name_version.pop()
        name = "-".join(name_version)

        package_path_by_name[name] = path_prefix

    return package_path_by_name


def write_packages_json(packages, name):
    temp_file = get_temp_file(name)
    write_data_to_json_file(path=temp_file, data=packages)
    return temp_file


def get_cpan_packageurls(name, path_prefix, logger=None):
    packageurls = []

    # file extensions found in cpan index
    ignorable_extensions = [".meta", ".readme", ".tar.gz"]

    cpan_authors_path = "/authors/id/"
    cpan_authors_url = CPAN_REPO + cpan_authors_path

    cpan_author_page_url = cpan_authors_url + path_prefix

    response = requests.get(cpan_author_page_url)
    if not response.ok:
        return packageurls

    if logger:
        logger(f"Getting package versions for {name} from {cpan_author_page_url}")

    soup = BeautifulSoup(response.text, "html.parser")
    package_list_elements = soup.find("ul").text.split("\n")

    package_elements = [
        element.replace(" ", "")
        for element in package_list_elements
        if element and element not in {" Parent Directory", " CHECKSUMS"}
    ]

    versions = []
    for package_file in package_elements:
        for extension in ignorable_extensions:
            if extension in package_file:
                package_file = package_file.replace(extension, "")

        name_version = package_file.split("-")
        version = name_version.pop()
        package_name = "-".join(name_version)
        if package_name != name:
            continue

        versions.append(version)

    unique_versions = list(set(versions))
    for version in unique_versions:
        purl = PackageURL(
            type=CPAN_TYPE,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls
