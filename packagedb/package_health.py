#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import timedelta

from django.utils import timezone
from fetchcode.package import info
from packageurl import PackageURL
from univers.version_range import RANGE_CLASS_BY_SCHEMES
from univers.versions import InvalidVersion

from packagedb.models import Package
from packagedb.models import PackageHealthMetrics

HEALTH_METRICS_MAX_AGE = timedelta(days=7)

NpmVersion = RANGE_CLASS_BY_SCHEMES["npm"].version_class


def _sort_by_version(packages):
    """
    Return packages sorted by npm version using univers SemverVersion.

    Packages with missing or invalid versions are dropped. Each version is
    parsed once for both validation and sorting.
    """
    packages_with_versions = []
    for package in packages:
        try:
            packages_with_versions.append((NpmVersion(package.version), package))
        except (InvalidVersion, TypeError):
            continue

    packages_with_versions.sort(key=lambda item: item[0])
    return [package for _version, package in packages_with_versions]


def get_fresh_health_metrics(package, version):
    """
    Return the most recent PackageHealthMetrics for `package` / `version` if
    it is no older than HEALTH_METRICS_MAX_AGE, otherwise return None.
    """
    cutoff = timezone.now() - HEALTH_METRICS_MAX_AGE
    return (
        PackageHealthMetrics.objects.select_related("package")
        .filter(
            package=package,
            version=version,
            date_collected__gte=cutoff,
        )
        .order_by("-date_collected")
        .first()
    )


def get_npm_data_from_fetchcode(purl):
    """
    Return a mapping with ``version``, ``download_url``, and ``vcs_url`` for the
    latest version of an npm ``purl`` using fetchcode.

    Return None if fetchcode cannot resolve the package.
    """
    try:
        packages = [p for p in info(str(purl)) or []]
    except Exception:
        return None

    if not packages:
        return None

    packages_with_version = [p for p in packages if p.version]
    sorted_packages = _sort_by_version(packages_with_version)
    if sorted_packages:
        latest = sorted_packages[-1]
    else:
        latest = packages[0]

    return {
        "version": latest.version or "",
        "download_url": latest.download_url or "",
        "vcs_url": latest.vcs_url or "",
    }


def run_scio_health_pipeline(repo_url):
    """
    Run the SCIO health-metrics pipeline for `repo_url` and return metrics.

    The SCIO pipeline does not exist yet. This stub returns a placeholder
    mapping so callers can store results in PackageHealthMetrics.
    """
    # TODO: Replace with a real SCIO pipeline invocation when available.
    return {
        "repo_url": repo_url,
        "score": None,
        "status": "pending_scio_pipeline",
        "note": "SCIO health pipeline is not implemented; placeholder metrics.",
    }


def _npm_registry_url(namespace, name):
    """Return a unique npm registry metadata URL for a versionless package."""
    package_name = f"{namespace}/{name}" if namespace else name
    return f"https://registry.npmjs.org/{package_name}"


def get_or_create_versionless_npm_package(purl):
    """
    Return ``(package, latest_version, repo_url, error)`` for a versionless npm PURL.

    Fetches package metadata from fetchcode once. Looks up or creates a
    versionless Package using type, namespace, name, and registry download_url.
    ``latest_version`` and ``repo_url`` come from that single fetchcode call.
    """
    package_url = PackageURL.from_string(purl)
    namespace = package_url.namespace or ""

    fetchcode_data = get_npm_data_from_fetchcode(purl)
    if not fetchcode_data or not fetchcode_data["version"]:
        return None, None, None, f"Could not resolve package data for {purl} via fetchcode."

    latest_version = fetchcode_data["version"]
    repo_url = fetchcode_data["vcs_url"] or None
    download_url = _npm_registry_url(namespace, package_url.name)

    package, _created = Package.objects.get_or_create(
        type=package_url.type,
        namespace=namespace,
        name=package_url.name,
        download_url=download_url,
    )

    return package, latest_version, repo_url, None


def fetch_and_store_health_metrics(package, version, repo_url):
    """
    Run the SCIO health pipeline for ``repo_url`` and store metrics.

    Return a tuple of (PackageHealthMetrics, error_message).
    On success, error_message is None. On failure, PackageHealthMetrics is None.
    """
    if not repo_url:
        return None, "Could not determine repository URL via fetchcode."

    metrics = run_scio_health_pipeline(repo_url)
    health_metrics = PackageHealthMetrics.objects.create(
        package=package,
        version=version,
        metrics=metrics,
        date_collected=timezone.now(),
    )
    # Avoid an extra Package query when serializing ``purl``.
    health_metrics.package = package
    return health_metrics, None
