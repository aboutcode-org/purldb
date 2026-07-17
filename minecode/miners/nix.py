#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packagedcode import models as scan_models
from packageurl import PackageURL

import requests


def get_nix_download_url(path):
    """
    Construct a download url from cache.nixos.org based on the /nix/store/
    path
    """
    narinfo_hash = path.replace("/nix/store/", "").split("-")[0]
    narinfo_url = f"https://cache.nixos.org/{narinfo_hash}.narinfo"
    url_path = get_narinfo_url(narinfo_url)
    return f"https://cache.nixos.org/{url_path}"


def get_narinfo_url(narinfo_url):
    """
    Visit the narinfo url, parsed and return the URL value
    """
    # Fetch the narinfo file
    response = requests.get(narinfo_url)
    response.raise_for_status()

    # Parse line by line
    for line in response.text.splitlines():
        if line.startswith("URL:"):
            # Strip off "URL:" and any whitespace
            return line.split(":", 1)[1].strip()
    return None


def build_packages(metadata_dict, purl):
    package_version = purl.version

    description = metadata_dict.get("summary", "")
    homepage_url = metadata_dict.get("homepage_url", "")
    license = metadata_dict.get("license", [])
    extracted_license_statement = license if isinstance(license, list) else [license]

    releases = metadata_dict.get("releases", [])
    for release in releases:
        version = release.get("version", "")
        if package_version and version != package_version:
            continue
        common_data = dict(
            name=purl.name,
            namespace=purl.namespace,
            version=version,
            description=description,
            homepage_url=homepage_url,
            extracted_license_statement=extracted_license_statement,
        )

        platforms = release.get("platforms", "")
        for platform in platforms:
            date = platform.get("date") or None
            platform_system = platform.get("system", "")
            commit = platform.get("commit_hash", "")
            platform_outputs = platform.get("outputs") or None

            if not platform_outputs:
                continue
            for platform_output in platform_outputs:
                output_name = platform_output.get("name")
                path = platform_output.get("path")
                narinfo_url = path.replace("/nix/store/", "").split("-")[0]
                download_url = get_nix_download_url(narinfo_url)
                download_data = dict(
                    datasource_id="nix_pkginfo",
                    type="nix",
                    download_url=download_url,
                    release_date=date,
                )
                download_data.update(common_data)
                package = scan_models.PackageData.from_data(download_data)
                package.datasource_id = "nix_api_metadata"
                qualifiers = {}
                if platform_system:
                    qualifiers["system"] = platform_system
                if commit:
                    qualifiers["commit"] = commit
                if output_name:
                    qualifiers["output"] = output_name
                updated_purl = update_purl_with_version_qualifiers(purl, version, qualifiers)
                package.set_purl(updated_purl)
                yield package


def update_purl_with_version_qualifiers(purl, version, qualifiers):
    """
    Update a PackageURL with the given version and qualifiers.
    """
    return PackageURL(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=version,
        qualifiers=qualifiers,
        subpath=purl.subpath,
    )


def verify_url_existence(url):
    """
    Perform a fast HTTP HEAD request to check if a generated URL is valid.
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code == 200:
            return True
        elif response.status_code in (403, 429, 409):  # forbidden, rate limit, conflict
            return True  # resource exists but not accessible
        else:
            return False
    except Exception:
        return False
