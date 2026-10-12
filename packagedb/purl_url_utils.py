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
from packageurl.contrib import purl2url

logger = logging.getLogger(__name__)


def derive_download_url(purl_string, provided_download_url=None):
    """
    Return a download URL for the package identified by ``purl_string``.

    If ``provided_download_url`` is given it is returned as-is. Otherwise
    purl2url is used to infer a real download URL. When that also fails a
    synthetic URL is built from the PURL components so that the unique
    constraint on ``Package.download_url`` can still be satisfied.
    """
    if provided_download_url:
        return provided_download_url

    try:
        download_url = purl2url.get_download_url(purl_string)
        if download_url:
            return download_url
    except Exception:
        pass

    # Fall back to a synthetic URL so the uniqueness constraint is satisfied
    # even when no real download URL is available (e.g. packages from
    # federatedcode that only carry a PURL).
    try:
        purl = PackageURL.from_string(purl_string)
        return generate_synthetic_download_url(purl)
    except Exception as e:
        logger.warning(f"Could not generate download URL for {purl_string!r}: {e}")
        return f"purl:{purl_string}"


def generate_synthetic_download_url(purl):
    """
    Return a synthetic download URL for ``purl`` in the form:
        purl://<type>/<namespace>/<name>@<version>?<qualifiers>#<subpath>

    All PURL components that affect identity are included so that two
    packages which differ only by qualifier (e.g. Maven JARs with different
    classifiers) still receive distinct synthetic URLs.
    """
    parts = ["purl://", purl.type]

    if purl.namespace:
        parts += ["/", purl.namespace]

    parts += ["/", purl.name]

    if purl.version:
        parts += ["@", purl.version]

    if purl.qualifiers:
        qual_str = "&".join(f"{k}={v}" for k, v in sorted(purl.qualifiers.items()))
        parts += ["?", qual_str]

    if purl.subpath:
        parts += ["#", purl.subpath]

    return "".join(parts)
