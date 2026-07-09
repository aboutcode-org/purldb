#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import shutil
import subprocess
import json
from packageurl import PackageURL
from minecode.miners.nix import build_packages, verify_url_existence
from fetchcode import fetch_json_response

from minecode import priority_router
from packagedb.models import PackageContentType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def map_nix_package(package_url, pipelines, priority=0):
    """
    Add a composer `package_url` to the PackageDB.
    """
    from minecode.model_utils import add_package_to_scan_queue, merge_or_create_package

    # Check if the `nix` command is available on the system
    have_nix = False
    if shutil.which("nix") is not None:
        have_nix = True

    namespace = package_url.namespace
    # We will only work with the official nixpkgs repository.
    # It is impossible to handle all third‑party or custom repositories.
    if not namespace.lower() == "nixpkgs":
        return None

    data = get_nix_package_data(package_url)

    if not data and have_nix:
        data = get_nix_package_data_via_cli(package_url)
        clean_garbage()

    if data:
        packages = build_packages(data, package_url)

        error = None
        for package in packages:
            package.extra_data["package_content"] = PackageContentType.BINARY
            db_package, _, _, error = merge_or_create_package(package, visit_level=0)
            if error:
                break

            if db_package:
                add_package_to_scan_queue(
                    package=db_package, pipelines=pipelines, priority=priority
                )

        return error
    else:
        return f"Failed to fetch package data for {package_url}"


def get_nix_package_data(purl):
    """
    Fetch package data from https://search.devbox.sh/.
    """

    api_url = f"https://search.devbox.sh/v2/pkg?name={purl.name}"
    if not verify_url_existence(api_url):
        return None

    return fetch_json_response(api_url)


def parse_license(license_data):
    """
    Parse a license object and return a string representation of the license.
    """
    return (
        license_data.get("spdxId")
        or license_data.get("fullName")
        or license_data.get("shortName")
        or str(license_data)
    )


def get_nix_package_data_via_cli(package_url):
    """
    Fetch package metadata using the Nix CLI (mainly for packages that
    Devbox doesn't index).
    """
    # Create a Nix expression to pull just the fields we want.
    package_name = package_url.name
    package_version = package_url.version

    nix_exp = f"""
        let
            pkgs = import <nixpkgs> {{}};
            pkg = pkgs.{package_name};
            outputNames = if pkg ? outputs then pkg.outputs else ["out"];
        in {{
            name = pkg.pname or pkg.name or "";
            version = pkg.version or "";
            storePath = pkg.outPath or "";
            outputs = builtins.listToAttrs (map (name: {{ name = name; value = pkg.${{name}}.outPath; }}) outputNames);
            description = pkg.meta.description or "";
            homepage = pkg.meta.homepage or "";
            license = pkg.meta.license or {{}};
            system = pkg.system or "";
        }}
    """

    cmd = ["nix-instantiate", "--eval", "--json", "--strict", "-E", nix_exp]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        pkg_data = json.loads(result.stdout)

        version = pkg_data.get("version", "")
        if package_version:
            if not version or version != package_version:
                print(f"Cannot find version: {package_version}, got {version}")
                return None

        output_list = [
            {"name": pname, "path": ppath} for pname, ppath in pkg_data.get("outputs", {}).items()
        ]

        # Return a similar JSON layout as Devbox
        return {
            "summary": pkg_data.get("description", ""),
            "homepage_url": pkg_data.get("homepage", ""),
            "license": parse_license(pkg_data.get("license", {})),
            "releases": [
                {
                    "version": version,
                    "platforms": [{"system": pkg_data.get("system", ""), "outputs": output_list}],
                }
            ],
        }
    except Exception as e:
        print(
            f"Failed to fetch Nix package data for {package_url}: {e.stderr if hasattr(e, 'stderr') else e}"
        )
        return None


def clean_garbage():
    """
    Delete all unreferenced downloaded tarballs and evaluation caches
    """
    nix_store = shutil.which("nix-store")
    if nix_store:
        subprocess.run([nix_store, "--gc"], capture_output=True)  # noqa: S603
    else:
        raise FileNotFoundError("nix-store not found in PATH")


@priority_router.route("pkg:nix/nixpkgs/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a nix Package URL (PURL).
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    package_url = PackageURL.from_string(purl_str)

    error_msg = map_nix_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
