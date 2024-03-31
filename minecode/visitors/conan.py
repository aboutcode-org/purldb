#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging

import requests
import saneyaml
from packagedcode.conan import ConanFileHandler
from packageurl import PackageURL

from minecode import priority_router
from packagedb.models import PackageContentType

"""
Collect Conan packages from Conan Central.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_yaml_response(url):
    """
    Fetch YAML content from the url and return it as a dictionary.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.content.decode("utf-8")
        return saneyaml.load(content)
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")


def get_conan_recipe(name, version):
    """
    Return the contents of the `conanfile.py` and `conandata.yml` file for
    the conan package described by name and version string.
    """
    base_index_url = (
        "https://raw.githubusercontent.com/conan-io/"
        "conan-center-index/master/recipes/"
    )

    conan_central_config_url = f"{base_index_url}/{name}/config.yml"
    config = get_yaml_response(conan_central_config_url)
    if not config:
        return None, None

    versions = config.get("versions", {})
    recipe_location = versions.get(version, {})
    folder = recipe_location.get("folder")

    folder = recipe_location.get("folder")
    if not folder:
        logger.error(f"No folder found for version {version} of package {name}")
        return None, None

    conanfile_py_url = f"{base_index_url}/{name}/{folder}/conanfile.py"
    conandata_yml_url = f"{base_index_url}/{name}/{folder}/conandata.yml"

    conandata = get_yaml_response(conandata_yml_url)

    try:
        response = requests.get(conanfile_py_url)
        response.raise_for_status()
        conanfile = response.text
    except requests.exceptions.HTTPError as err:
        logger.error(
            f"HTTP error occurred while fetching conanfile.py for {name} {version}: {err}"
        )
        conanfile = None

    return conanfile, conandata


def get_download_info(conandata, version):
    """
    Return download_url and SHA256 hash from `conandata.yml`.
    """
    sources = conandata.get("sources", {})
    pkg_data = sources.get(version, {})

    download_url = pkg_data.get("url")
    sha256 = pkg_data.get("sha256")

    if isinstance(download_url, list):
        download_url = download_url[0]

    return download_url, sha256


def map_conan_package(package_url):
    """
    Add a conan `package_url` to the PackageDB.

    Return an error string if any errors are encountered during the process
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    conanfile, conandata = get_conan_recipe(
        name=package_url.name,
        version=package_url.version,
    )

    download_url, sha256 = get_download_info(conandata, package_url.version)

    if not conanfile:
        error = f"Package does not exist on conan central: {package_url}"
        logger.error(error)
        return error
    if not download_url:
        error = f"Package download_url does not exist on conan central: {package_url}"
        logger.error(error)
        return error

    package = ConanFileHandler._parse(conan_recipe=conanfile)
    package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
    package.version = package_url.version
    package.download_url = download_url
    package.sha256 = sha256

    db_package, _, _, error = merge_or_create_package(package, visit_level=0)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package)

    return error


@priority_router.route("pkg:conan/.*")
def process_request(purl_str):
    """
    Process `priority_resource_uri` containing a conan Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from
    https://github.com/conan-io/conan-center-index and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    package_url = PackageURL.from_string(purl_str)
    if not package_url.version:
        return

    error_msg = map_conan_package(package_url)

    if error_msg:
        return error_msg
