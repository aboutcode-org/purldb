#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from fetchcode.package_versions import versions
from packageurl import PackageURL

from minecode.model_utils import add_package_to_scan_queue
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageHealthMetrics
from packagedb.models import ScoringModel
from packagedb.tasks import VERSION_CLASS_BY_PACKAGE_TYPE
from purl2vcs.find_source_repo import add_source_package_to_package_set
from purl2vcs.find_source_repo import get_source_package_and_add_to_package_set

HEALTH_METRICS_PIPELINE = "scan_repo_health"
DEFAULT_HEALTH_SCORING_MODEL_VERSION = "0.1"


def health_metrics_max_age():
    """Return the freshness window for PackageHealthMetrics (from settings)."""
    days = getattr(settings, "HEALTH_METRICS_MAX_AGE_DAYS", 7)
    return timedelta(days=days)


def get_or_create_scoring_model(
    ecosystem="npmlargerecosystem",
    scoring_model="NPMMostUsed",
    model_version=DEFAULT_HEALTH_SCORING_MODEL_VERSION,
):
    """Return the ScoringModel row for ecosystem / approach / version."""
    model, _ = ScoringModel.objects.get_or_create(
        ecosystem=ecosystem,
        scoring_model=scoring_model,
        model_version=model_version,
    )
    return model


def get_fresh_health_metrics(package, version):
    """
    Return the most recent PackageHealthMetrics for ``package`` / ``version`` if
    it is no older than ``HEALTH_METRICS_MAX_AGE_DAYS``, otherwise return None.

    ``package`` should be the versionless npm BASE_PACKAGE.
    """
    cutoff = timezone.now() - health_metrics_max_age()
    return (
        PackageHealthMetrics.objects.select_related(
            "package", "source_package", "catalog_scoring_model"
        )
        .filter(
            package=package,
            version=version,
            date_collected__gte=cutoff,
        )
        .order_by("-date_collected")
        .first()
    )


def get_fresh_health_metrics_for_source(source_package):
    """
    Return the most recent fresh PackageHealthMetrics for ``source_package``.

    Used when several npm packages share one SOURCE_BASE_PACKAGE (monorepo): a
    scan already collected for that source can be reused for another npm PURL.
    """
    if source_package is None:
        return None
    cutoff = timezone.now() - health_metrics_max_age()
    return (
        PackageHealthMetrics.objects.select_related(
            "package", "source_package", "catalog_scoring_model"
        )
        .filter(
            source_package=source_package,
            date_collected__gte=cutoff,
        )
        .order_by("-date_collected")
        .first()
    )


def adopt_source_health_metrics(npm_package, source_metrics, version):
    """
    Create PackageHealthMetrics for ``npm_package`` by copying scan fields from
    an existing row for the same source repository.

    Preserve ``date_collected`` so the adopted row stays within the freshness
    window of the original source scan.
    """
    return PackageHealthMetrics.objects.create(
        package=npm_package,
        source_package=source_metrics.source_package,
        catalog_scoring_model=source_metrics.catalog_scoring_model,
        vcs_url=source_metrics.vcs_url,
        scoring_model=source_metrics.scoring_model,
        score=source_metrics.score,
        commit_range=source_metrics.commit_range,
        run_start_date=source_metrics.run_start_date,
        run_end_date=source_metrics.run_end_date,
        metrics=source_metrics.metrics,
        version=version or source_metrics.version,
        date_collected=source_metrics.date_collected,
    )


def resolve_fresh_health_metrics(base_package, source_package, latest_version):
    """
    Return fresh PackageHealthMetrics for ``base_package``, adopting from the
    shared ``source_package`` when another npm package already has a fresh scan.
    """
    fresh = get_fresh_health_metrics(base_package, latest_version)
    if fresh:
        return fresh

    sibling = get_fresh_health_metrics_for_source(source_package)
    if not sibling:
        return None

    if sibling.package_id == base_package.id and sibling.version == latest_version:
        return sibling

    return adopt_source_health_metrics(base_package, sibling, latest_version)


def resolve_npm_package_for_health(source_package):
    """
    Return the npm BASE_PACKAGE linked to the scanned ``source_package``.

    Prefer a value stashed on the SOURCE_BASE_PACKAGE while a scan was queued
    (``extra_data.health_npm_purl``), then the related npm BASE_PACKAGE in the
    same package set.
    """
    stashed = (source_package.extra_data or {}).get("health_npm_purl") or ""
    if stashed:
        base = get_versionless_base_package(stashed)
        if base:
            return base
        return ensure_versionless_base_package(stashed)

    for package_set in source_package.package_sets.all():
        base = package_set.packages.filter(
            type="npm",
            package_content=PackageContentType.BASE_PACKAGE,
        ).first()
        if base:
            return base
        npm_package = (
            package_set.packages.filter(type="npm").exclude(name="").order_by("version").first()
        )
        if npm_package:
            versionless = str(
                PackageURL(
                    type="npm",
                    namespace=npm_package.namespace,
                    name=npm_package.name,
                )
            )
            return ensure_versionless_base_package(versionless)
    return None


def _npm_registry_url(namespace, name):
    """Return a unique npm registry metadata URL for a versionless package."""
    package_name = f"{namespace}/{name}" if namespace else name
    return f"https://registry.npmjs.org/{package_name}"


def get_latest_npm_version(purl):
    """
    Return the latest npm version string for ``purl`` using fetchcode
    ``package_versions.versions`` (same approach as PackageWatch).

    Return None if versions cannot be resolved.
    """
    version_class = VERSION_CLASS_BY_PACKAGE_TYPE.get("npm")
    if not version_class:
        return None

    try:
        all_versions = versions(purl) or []
        parsed = [version_class(entry.value) for entry in all_versions]
    except Exception:
        # Includes InvalidVersion and fetchcode registry errors (HTTP 404, etc.).
        return None

    if not parsed:
        return None

    parsed.sort()
    return str(parsed[-1])


def collect_latest_npm_package(package_url):
    """
    Collect a versioned npm PackageURL into PackageDB using the same registry
    path as ``minecode.collectors.npm.map_npm_package``, but without queueing a
    DEFAULT_PIPELINES scan (health queues ``scan_repo_health`` separately).

    Return ``(db_package, error)``.
    """
    from packagedcode.npm import NpmPackageJsonHandler

    from minecode.collectors.npm import get_package_json
    from minecode.model_utils import merge_or_create_package

    package_json = get_package_json(
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
    )
    if not package_json:
        return None, f"Package does not exist on npmjs: {package_url}"

    package_data = NpmPackageJsonHandler._parse(json_data=package_json)
    package_data.extra_data["package_content"] = PackageContentType.SOURCE_ARCHIVE
    db_package, _, _, error = merge_or_create_package(package_data, visit_level=0)
    return db_package, error or None


def get_versionless_base_package(purl):
    """
    Return the versionless BASE_PACKAGE for an npm ``purl``, or None if it does
    not exist yet.
    """
    package_url = PackageURL.from_string(purl)
    namespace = package_url.namespace or ""
    download_url = _npm_registry_url(namespace, package_url.name)
    return Package.objects.filter(
        type=package_url.type,
        namespace=namespace,
        name=package_url.name,
        download_url=download_url,
        package_content=PackageContentType.BASE_PACKAGE,
    ).first()


def ensure_versionless_base_package(purl):
    """Get or create the versionless BASE_PACKAGE row for an npm ``purl``."""
    package_url = PackageURL.from_string(purl)
    namespace = package_url.namespace or ""
    download_url = _npm_registry_url(namespace, package_url.name)
    base_package, _ = Package.objects.get_or_create(
        type=package_url.type,
        namespace=namespace,
        name=package_url.name,
        download_url=download_url,
        package_content=PackageContentType.BASE_PACKAGE,
    )
    return base_package


def get_source_package(package):
    """
    Return a SOURCE_BASE_PACKAGE or SOURCE_REPO Package linked to ``package``
    via PackageSet, or None.
    """
    if package is None:
        return None

    if package.package_content in (
        PackageContentType.SOURCE_BASE_PACKAGE,
        PackageContentType.SOURCE_REPO,
    ):
        return package

    for package_set in package.package_sets.all():
        source = package_set.packages.filter(
            package_content__in=(
                PackageContentType.SOURCE_BASE_PACKAGE,
                PackageContentType.SOURCE_REPO,
            ),
        ).first()
        if source:
            return source

    return None


def get_versionless_source_package(package):
    """Return a versionless SOURCE_BASE_PACKAGE linked to ``package``, or None."""
    source = get_source_package(package)
    if source is None:
        return None
    if source.package_content == PackageContentType.SOURCE_BASE_PACKAGE and source.version == "":
        return source

    for package_set in package.package_sets.all():
        versionless = package_set.packages.filter(
            package_content=PackageContentType.SOURCE_BASE_PACKAGE,
            version="",
        ).first()
        if versionless:
            return versionless
    return None


def get_versioned_source_package(package, version):
    """Return a SOURCE_REPO Package for ``version`` linked to ``package``, or None."""
    if not version:
        return None

    for package_set in package.package_sets.all():
        versioned = package_set.packages.filter(
            package_content=PackageContentType.SOURCE_REPO,
            version=version,
        ).first()
        if versioned:
            return versioned

    source = get_source_package(package)
    if (
        source
        and source.package_content == PackageContentType.SOURCE_REPO
        and source.version == version
    ):
        return source
    return None


def resolve_source_package(base_package, latest_package=None):
    """
    Resolve versionless SOURCE_BASE_PACKAGE and versioned SOURCE_REPO for
    ``base_package``.

    Both rows are created through purl2vcs ``get_source_package_and_add_to_package_set``:
    - versionless BASE_PACKAGE → fetchcode repo URL with version stripped
      (SOURCE_BASE_PACKAGE)
    - latest npm package → tag/commit matching (SOURCE_REPO)

    Return ``(versionless_source_package, error)``.
    """
    versionless_source = get_versionless_source_package(base_package)
    if versionless_source:
        return versionless_source, None

    get_source_package_and_add_to_package_set(base_package, queue_scan=False)
    if latest_package is not None:
        get_source_package_and_add_to_package_set(latest_package, queue_scan=False)
        versionless_source = get_versionless_source_package(base_package)
        versioned_source = get_versioned_source_package(
            base_package, latest_package.version
        ) or get_versioned_source_package(latest_package, latest_package.version)
        if versionless_source and versioned_source:
            add_source_package_to_package_set(
                source_package=versionless_source,
                package=versioned_source,
            )

    versionless_source = get_versionless_source_package(base_package)
    if not versionless_source:
        return None, "No source package found"
    return versionless_source, None


def collect_versionless_npm_package(purl):
    """
    Collect a versionless npm PURL into PackageDB.

    Reuses:
    - fetchcode ``versions`` for latest (watch)
    - npm collector registry parse + ``merge_or_create_package`` (collect)
    Both rows are created through purl2vcs ``get_source_package_and_add_to_package_set`` for versionless
      SOURCE_BASE_PACKAGE (fetchcode + strip version) and versioned SOURCE_REPO (tags)

    Also ensures a BASE_PACKAGE identity row (registry metadata URL).

    Return ``(base_package, source_package, latest_version, error)``.
    """
    package_url = PackageURL.from_string(purl)

    latest_version = get_latest_npm_version(purl)
    if not latest_version:
        return None, None, None, f"Could not resolve latest version for {purl}."

    versioned_purl = PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=latest_version,
    )
    latest_package, error = collect_latest_npm_package(versioned_purl)
    if error:
        return None, None, latest_version, error

    base_package = ensure_versionless_base_package(purl)
    add_source_package_to_package_set(
        source_package=latest_package,
        package=base_package,
    )

    source_package, source_error = resolve_source_package(
        base_package=base_package,
        latest_package=latest_package,
    )
    if source_error:
        return base_package, None, latest_version, source_error

    return base_package, source_package, latest_version, None


def ensure_source_package_for_base(base_package, purl):
    """
    Ensure ``base_package`` has a linked SOURCE_REPO and return the latest npm
    version string.

    Return ``(source_package, latest_version, error)``.
    """
    latest_version = get_latest_npm_version(purl)
    if not latest_version:
        return None, None, f"Could not resolve latest version for {purl}."

    package_url = PackageURL.from_string(purl)
    versioned_purl = PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=latest_version,
    )

    latest_package = Package.objects.filter(
        type=versioned_purl.type,
        namespace=versioned_purl.namespace or "",
        name=versioned_purl.name,
        version=latest_version,
    ).first()

    if latest_package is None:
        latest_package, error = collect_latest_npm_package(versioned_purl)
        if error:
            return None, latest_version, error
        add_source_package_to_package_set(
            source_package=base_package,
            package=latest_package,
        )

    source_package, source_error = resolve_source_package(
        base_package=base_package,
        latest_package=latest_package,
    )
    if source_error:
        return None, latest_version, source_error

    return source_package, latest_version, None


def queue_health_metrics_scan(source_package, npm_purl=None, priority=100):
    """
    Queue ``scan_repo_health`` for ``source_package`` via ScannableURI.

    When ``npm_purl`` is given, stash it on ``source_package.extra_data`` so the
    webhook can resolve the npm BASE_PACKAGE to store on PackageHealthMetrics.

    If a ScannableURI for this source is already in flight (``new`` /
    ``submitted`` / ``in progress``), reuse it. If the latest URI finished
    successfully or in a terminal failure (``failed`` / ``timeout`` /
    ``index failed``) and we need a new scan (missing or stale metrics),
    create a **new** ScannableURI. Resetting a finished URI reuses its UUID and
    ScanCode.io rejects the project as a duplicate name.
    Return the ScannableURI.
    """
    from minecode.models import ScannableURI

    if npm_purl:
        extra_data = dict(source_package.extra_data or {})
        if extra_data.get("health_npm_purl") != npm_purl:
            extra_data["health_npm_purl"] = npm_purl
            source_package.extra_data = extra_data
            source_package.save(update_fields=["extra_data"])

    pipelines = [HEALTH_METRICS_PIPELINE]
    scannable_uri = (
        ScannableURI.objects.filter(
            package=source_package,
            pipelines=pipelines,
        )
        .order_by("-id")
        .first()
    )

    if scannable_uri is None:
        add_package_to_scan_queue(
            source_package,
            pipelines=pipelines,
            priority=priority,
        )
        return (
            ScannableURI.objects.filter(
                package=source_package,
                pipelines=pipelines,
            )
            .order_by("-id")
            .first()
        )

    in_flight = {
        ScannableURI.SCAN_NEW,
        ScannableURI.SCAN_SUBMITTED,
        ScannableURI.SCAN_IN_PROGRESS,
    }
    if scannable_uri.scan_status in in_flight:
        if scannable_uri.priority < priority:
            scannable_uri.priority = priority
            scannable_uri.save(update_fields=["priority"])
        return scannable_uri

    # Finished earlier (indexed, scanned, or terminal failure). Always create a
    # new ScannableURI so ScanCode.io gets a fresh project UUID/name.
    return ScannableURI.objects.create(
        uri=source_package.download_url,
        package=source_package,
        pipelines=pipelines,
        priority=priority,
        reindex_uri=True,
    )


def write_package_health_metrics(package, project_extra_data=None):
    """
    Persist PackageHealthMetrics from ScanCode.io project ``extra_data``.

    ``package`` is the scanned SOURCE_BASE_PACKAGE (github). The metrics row
    stores that as ``source_package`` and the related npm BASE_PACKAGE as
    ``package``.

    ``extra_data`` shape::

        {
          "vcs_url": "...",
          "scoring_model": "...",
          "score": 0.0,
          "commit_range": {...},
          "run_start_date": "...",
          "run_end_date": "...",
          "metrics": {...}
        }

    Return the created row, or None if ``metrics`` is missing.
    """
    source_package = package
    extra_data = project_extra_data if isinstance(project_extra_data, dict) else {}
    metrics = extra_data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return None

    try:
        score = float(extra_data.get("score"))
    except (TypeError, ValueError):
        score = 0.0

    commit_range = extra_data.get("commit_range")
    if not isinstance(commit_range, (dict, list)):
        commit_range = {}

    npm_package = resolve_npm_package_for_health(source_package)
    if npm_package is None:
        return None

    version = ""
    for package_set in source_package.package_sets.all():
        versioned_npm = (
            package_set.packages.filter(type="npm").exclude(version="").order_by("-version").first()
        )
        if versioned_npm and versioned_npm.version:
            version = versioned_npm.version
            break
    if not version:
        version = npm_package.version or source_package.version or ""

    return PackageHealthMetrics.objects.create(
        package=npm_package,
        source_package=source_package,
        catalog_scoring_model=get_or_create_scoring_model(),
        vcs_url=str(extra_data.get("vcs_url") or ""),
        scoring_model=str(extra_data.get("scoring_model") or ""),
        score=score,
        commit_range=commit_range,
        run_start_date=_parse_health_datetime(extra_data.get("run_start_date")),
        run_end_date=_parse_health_datetime(extra_data.get("run_end_date")),
        metrics=metrics,
        version=version,
        date_collected=timezone.now(),
    )


def _parse_health_datetime(value):
    """Parse an ISO datetime from scan extra_data, or return None."""
    from datetime import datetime

    from django.utils.dateparse import parse_datetime

    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.utc)
        return value
    try:
        parsed = parse_datetime(str(value))
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.utc)
    return parsed


def resolve_health_request(purl):
    """
    Resolve a health-metrics request for a versionless npm ``purl``.

    Return a mapping with keys:
    - ``fresh_metrics``: PackageHealthMetrics or None
    - ``base_package``: npm BASE_PACKAGE or None
    - ``source_package``: SOURCE_BASE_PACKAGE or None
    - ``latest_version``: str or None
    - ``scannable_uri``: ScannableURI or None (set when a job is queued)
    - ``error``: str or None
    """
    base_package = get_versionless_base_package(purl)

    if base_package is None:
        base_package, source_package, latest_version, error = collect_versionless_npm_package(purl)
        if error:
            return {
                "fresh_metrics": None,
                "base_package": None,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": error,
            }
        if source_package is None:
            return {
                "fresh_metrics": None,
                "base_package": base_package,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": "No source package found",
            }
    else:
        source_package, latest_version, error = ensure_source_package_for_base(base_package, purl)
        if error:
            return {
                "fresh_metrics": None,
                "base_package": base_package,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": error,
            }

    fresh_metrics = resolve_fresh_health_metrics(
        base_package, source_package, latest_version
    )
    if fresh_metrics:
        return {
            "fresh_metrics": fresh_metrics,
            "base_package": base_package,
            "source_package": source_package,
            "latest_version": latest_version,
            "scannable_uri": None,
            "error": None,
        }

    scannable_uri = queue_health_metrics_scan(source_package, npm_purl=base_package.package_url)
    return {
        "fresh_metrics": None,
        "base_package": base_package,
        "source_package": source_package,
        "latest_version": latest_version,
        "scannable_uri": scannable_uri,
        "error": None,
    }
