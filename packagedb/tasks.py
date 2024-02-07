#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import datetime

import django_rq
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS
from univers.version_range import RANGE_CLASS_BY_SCHEMES
from univers.versions import InvalidVersion

PRIORITY_QUEUE_SUPPORTED_ECOSYSTEMS = ["maven", "npm"]

VERSION_CLASS_BY_PACKAGE_TYPE = {
    pkg_type: range_class.version_class
    for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()
}


@django_rq.job("default")
def watch_new_packages(purl):
    """
    Collect new versions of a package and insert the
    new PURLs in PriorityResourceURI for indexing.
    Update the error message if any.
    """
    from packagedb.models import PackageWatch

    watch = PackageWatch.objects.get(package_url=purl)

    if not is_supported_watch_ecosystem(watch):
        return

    watch.watch_error = get_and_index_new_purls(watch.package_url)

    watch.last_watch_date = datetime.datetime.now(tz=datetime.timezone.utc)
    watch.save(update_fields=["last_watch_date", "watch_error"])


def get_and_index_new_purls(package_url):
    """
    Get new versions of a package and insert the
    new PURLs in PriorityResourceURI for indexing.
    Return error message if any.
    """
    from fetchcode.package_versions import versions
    from packageurl import PackageURL

    from minecode.models import PriorityResourceURI
    from packagedb.models import Package

    purl = PackageURL.from_string(package_url)
    version_class = VERSION_CLASS_BY_PACKAGE_TYPE.get(purl.type)

    local_versions = Package.objects.filter(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
    ).values_list("version", flat=True)

    all_versions = versions(package_url) or []

    try:
        local_versions = [version_class(version) for version in local_versions]
        all_versions = [version_class(version.value) for version in all_versions]
    except InvalidVersion as e:
        return f"InvalidVersion exception: {e}"

    for version in all_versions:
        if version in local_versions:
            continue
        new_purl = str(
            PackageURL(
                type=purl.type,
                namespace=purl.namespace,
                name=purl.name,
                version=str(version),
            )
        )
        PriorityResourceURI.objects.insert(new_purl)


def is_supported_watch_ecosystem(watch):
    """
    Check if PackageWatch.type ecosystem is supported in
    `fetchcode`, `PriorityResourceURI`, and `Univers`.
    If not supported update the `watch_error` field with error message.
    """
    for ecosystem, error_message in [
        (SUPPORTED_ECOSYSTEMS, "fetchcode"),
        (PRIORITY_QUEUE_SUPPORTED_ECOSYSTEMS, "Priority Queue"),
        (VERSION_CLASS_BY_PACKAGE_TYPE, "Univers"),
    ]:
        if watch.type not in ecosystem:
            watch.watch_error = (
                f"`{watch.type}` ecosystem is not supported by {error_message}"
            )
            watch.last_watch_date = datetime.datetime.now(tz=datetime.timezone.utc)
            watch.save(update_fields=["last_watch_date"])
            return False

    return True
