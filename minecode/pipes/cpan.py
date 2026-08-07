# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import gzip
import requests

from bs4 import BeautifulSoup
from packageurl import PackageURL

from minecode.utils import get_temp_file
from minecode.utils import grouper

CPAN_REPO = "https://www.cpan.org/"
CPAN_TYPE = "cpan"

# If True, show full details on fetching packageURL for
# a package name present in the index
LOG_PACKAGEURL_DETAILS = False

PACKAGE_BATCH_SIZE = 500


def get_cpan_packages(cpan_repo=CPAN_REPO, logger=None):
    """
    Get cpan package names parsed from the `02packages.details.txt`
    which contains a list of all modules and their respective
    package archive paths. We parse the package names and their respective
    path_prefixes with author page path from this list.
    """
    cpan_packages_url = cpan_repo + "modules/02packages.details.txt.gz"
    packages_archive = get_temp_file(file_name="cpan_packages", extension=".gz")
    packages_content = get_temp_file(file_name="cpan_packages", extension=".txt")
    response = requests.get(cpan_packages_url, stream=True)
    with open(packages_archive, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    with gzip.open(packages_archive, "rb") as f_in:
        with open(packages_content, "wb") as f_out:
            f_out.writelines(f_in)

    with open(packages_content, encoding="utf-8") as file:
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
    package_list = soup.find("ul")
    if not package_list:
        return packageurls

    package_list_elements = package_list.text.split("\n")

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


def mine_cpan_packages(logger=None):
    if logger:
        logger("Getting packages from cpan index")

    package_path_by_name = get_cpan_packages(cpan_repo=CPAN_REPO, logger=logger)

    if logger:
        packages_count = len(package_path_by_name.keys())
        logger(f"Mined {packages_count} packages from cpan index")

    return package_path_by_name


def mine_and_publish_cpan_packageurls(package_path_by_name, logger=None):
    if not package_path_by_name:
        return

    for package_batch in grouper(n=PACKAGE_BATCH_SIZE, iterable=package_path_by_name.keys()):
        packages_mined = []

        if logger and LOG_PACKAGEURL_DETAILS:
            logger("Starting package mining for a batch of packages")

        for package_name in package_batch:
            if not package_name or package_name in packages_mined:
                continue

            # fetch packageURLs for package
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"getting packageURLs for package: {package_name}")

            path_prefix = package_path_by_name.get(package_name)
            if not path_prefix:
                continue

            packageurls = get_cpan_packageurls(
                name=package_name,
                path_prefix=path_prefix,
                logger=logger,
            )
            if not packageurls:
                if logger and LOG_PACKAGEURL_DETAILS:
                    logger(f"Package versions not present for package: {package_name}")

                # We don't want to try fetching versions for these again
                packages_mined.append(package_name)
                continue

            # get repo and path for package
            base_purl = PackageURL(type=CPAN_TYPE, name=package_name).to_string()
            if logger and LOG_PACKAGEURL_DETAILS:
                logger(f"fetched packageURLs for package: {base_purl}")
                purls_string = " ".join(packageurls)
                logger(f"packageURLs: {purls_string}")

            packages_mined.append(package_name)
            yield base_purl, packageurls, []
