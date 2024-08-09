#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packageurl import PackageURL
from minecode import priority_router

from minecode.collectors.generic import map_fetchcode_supported_package

# Indexing OpenSSL PURLs requires a GitHub API token.
# Please add your GitHub API key to the `.env` file, for example: `GH_TOKEN=your-github-api`.
@priority_router.route('pkg:openssl/openssl@.*')
def process_request_dir_listed(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a OpenSSL Package URL (PURL)
    supported by fetchcode.

    This involves obtaining Package information for the PURL using
    https://github.com/nexB/fetchcode and using it to create a new
    PackageDB entry. The package is then added to the scan queue afterwards.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    addon_pipelines = kwargs.get('addon_pipelines', [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get('priority', 0)

    try:
        package_url = PackageURL.from_string(purl_str)
    except ValueError as e:
        error = f"error occurred when parsing {purl_str}: {e}"
        return error

    error_msg = map_fetchcode_supported_package(package_url, pipelines, priority)

    if error_msg:
        return error_msg
