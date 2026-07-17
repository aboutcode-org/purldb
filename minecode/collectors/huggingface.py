#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
from packageurl import PackageURL
import requests
from minecode import priority_router

from packagedb.models import PackageContentType
from packagedcode import models as scan_models

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def fetch_license_text(license_url):
    """
    Try to fetch LICENSE from the package.extra_data['hf_meta']['license_url'].
    If found, set package.extra_data['license_text'] and return True.
    """
    try:
        resp = requests.get(license_url, timeout=10)
        if resp.status_code == 200:
            return resp.text
        else:
            logger.info(f"License not found at {license_url}: status {resp.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error fetching license from {license_url}: {e}")


def get_hf_model_api(namespace, name):
    """
    Return the contents of the Hugging Face model API:
    https://huggingface.co/api/models/{namespace}/{name}
    """
    url = f"https://huggingface.co/api/models/{namespace}/{name}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as err:
        logger.error(f"Error fetching model data from HuggingFace: {err}")
        return None


def find_siblings_with_bin(siblings):
    """
    Return the first sibling (dict) that endswith '.bin' or '.pt' or '.safetensors'
    or None if none found.
    """
    if not siblings:
        return None
    for s in siblings:
        filename = s.get("rfilename") or s.get("filename") or s.get("name")
        if filename.endswith(".bin"):
            yield filename
    return None


def build_resolve_url(namespace, name, sha, filename):
    """
    Build the HuggingFace resolve URL for a given file.

    Example:
    https://huggingface.co/{namespace}/{name}/resolve/{sha}/{filename}

    """
    return f"https://huggingface.co/{namespace}/{name}/resolve/{sha}/{filename}"


def map_huggingface_package(package_url, pipelines, priority=0):
    """
    Add a huggingface `package_url` to the PackageDB.
    Expect PURL like: pkg:huggingface/{namespace}/{name}@{sha}
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    namespace = package_url.namespace
    name = package_url.name
    version = package_url.version

    if not namespace:
        error = f"HuggingFace PURL must include a namespace: {package_url}"
        logger.error(error)
        return error

    if not version:
        error = f"HuggingFace PURL must include a version/sha: {package_url}"
        logger.error(error)
        return error

    model_data = get_hf_model_api(namespace, name)
    if model_data is None:
        error = f"Unable to fetch model metadata for {namespace}/{name}"
        logger.error(error)
        return error

    siblings = model_data.get("siblings") or []
    first_sibling = siblings[0] if siblings else {}

    filename = (
        first_sibling.get("rfilename") or first_sibling.get("filename") or first_sibling.get("name")
    )

    resolve_url = build_resolve_url(namespace, name, version, filename)

    try:
        head_resp = requests.head(resolve_url, timeout=10)
        head_resp.raise_for_status()
    except requests.RequestException as err:
        error = f"Error fetching model file from HuggingFace for purl {package_url!r}: {err}"
        logger.error(error)
        return error

    license_url = build_resolve_url(namespace, name, version, "LICENSE")
    license_statement = fetch_license_text(license_url=license_url)
    parties = [scan_models.Party(name=model_data.get("author"), role="author")]

    for file in find_siblings_with_bin(siblings):
        download_url = build_resolve_url(namespace=namespace, name=name, sha=version, filename=file)

        package = scan_models.Package(
            type="huggingface",
            namespace=namespace,
            name=name,
            version=version,
            download_url=download_url,
            homepage_url=f"https://huggingface.co/{namespace}/{name}",
            parties=parties,
            extracted_license_statement=license_statement,
            release_date=model_data.get("createdAt"),
            api_data_url=f"https://huggingface.co/api/models/{namespace}/{name}",
        )

        package.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE

        db_package, _, _, error = merge_or_create_package(package, visit_level=0)

        if error:
            break

        if db_package:
            add_package_to_scan_queue(package=db_package, pipelines=pipelines, priority=priority)

    return error


@priority_router.route("pkg:huggingface/.*")
def process_request(purl_str, **kwargs):
    """
    Process HuggingFace Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)
    error_msg = map_huggingface_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
