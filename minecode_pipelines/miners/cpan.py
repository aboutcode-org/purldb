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

"""
Visitors for cpan and cpan-like perl package repositories.
"""


CPAN_REPO = "https://www.cpan.org/"
CPAN_TYPE = "cpan"


def get_cpan_packages(cpan_repo=CPAN_REPO, logger=None):
    """
    Get cpan package names parsed from the `02packages.details.txt`
    which conatins a list of all modules and their respective
    package archive paths. We parse the package names and their respective
    path_prefixes with author page path from this list.
    """
    cpan_packages_url = cpan_repo + "modules/02packages.details.txt.gz"
    packages_archive = get_temp_file(file_name="cpan_packages", extension=".gz")
    packages_content = get_temp_file(file_name="cpan_packages", extension=".txt")
    response = requests.get(cpan_packages_url, stream=True)
    with open(packages_archive, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    with gzip.open(packages_archive, "rb") as f_in:
        with open(packages_content, "wb") as f_out:
            f_out.writelines(f_in)

    with open(packages_content, 'r', encoding='utf-8') as file:
        packages_content = file.read()

    package_path_by_name = {}

    # The ``modules/02packages.details.txt`` file has the following section
    # at the beginning of the file:
    #
    # File:         02packages.details.txt
    # URL:          http://www.cpan.org/modules/02packages.details.txt
    # Description:  Package names found in directory $CPAN/authors/id/
    # Columns:      package name, version, path
    # Intended-For: Automated fetch routines, namespace documentation.
    # Written-By:   PAUSE version 1.005
    # Line-Count:   268940
    # Last-Updated: Mon, 29 Sep 2025 22:29:02 GMT
    #
    # This information is there in first 10 lines, and the last line is an
    # empty line, both of which we are ignoring below

    modules = packages_content.split("\n")[9:-1]

    # A sample line from this module list looks like this:
    #
    # Crypt::Passphrase::SHA1::Base64   0.021  L/LE/LEONT/Crypt-Passphrase-0.021.tar.gz

    for module in modules:
        info = [section for section in module.split(" ") if section]

        # This is like: L/LE/LEONT/Crypt-Passphrase-0.021.tar.gz
        package_path = info[-1]
        path_segments = package_path.split("/")
        filename = path_segments.pop()
        path_prefix = "/".join(path_segments)

        name_version = filename.replace(".tar.gz", "").split("-")
        _version = name_version.pop()
        name = "-".join(name_version)

        # for the above example: name: Crypt-Passphrase, path_prefix: L/LE/LEONT/
        package_path_by_name[name] = path_prefix

    return package_path_by_name


def get_cpan_packageurls(name, path_prefix, logger=None):
    """
    Given a package name and it's path_prefix (author page path)
    return a list of packageURLs for that package.

    An author page (like https://www.cpan.org/authors/id/P/PT/PTC/) lists
    all versions of all packages released by the author, so we can scrape
    all the packageURLs from this author packages index.
    """

    author_name = path_prefix.split("/")[-1]

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

    # We get all the listed packages in the author page index
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
            namespace=author_name,
            name=name,
            version=version,
        )
        packageurls.append(purl.to_string())

    return packageurls
