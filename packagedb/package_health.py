#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
from datetime import timedelta

from django.utils import timezone
from fetchcode.package_versions import versions
from packageurl import PackageURL
from univers.versions import InvalidVersion

from minecode.model_utils import add_package_to_scan_queue
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageHealthMetrics
from packagedb.models import ScoringModel
from packagedb.tasks import VERSION_CLASS_BY_PACKAGE_TYPE
from purl2vcs.find_source_repo import add_source_package_to_package_set
from purl2vcs.find_source_repo import get_source_package_and_add_to_package_set

HEALTH_METRICS_MAX_AGE = timedelta(days=7)
HEALTH_METRICS_PIPELINE = "scan_repo_health"
DEFAULT_HEALTH_SCORING_MODEL_VERSION = "1.0"


def get_or_create_scoring_model(
    ecosystem="npm",
    scoring_model="health",
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
    it is no older than HEALTH_METRICS_MAX_AGE, otherwise return None.

    ``package`` should be the SOURCE_REPO Package health metrics are keyed to.
    """
    cutoff = timezone.now() - HEALTH_METRICS_MAX_AGE
    return (
        PackageHealthMetrics.objects.select_related("package", "scoring_model")
        .filter(
            package=package,
            version=version,
            date_collected__gte=cutoff,
        )
        .order_by("-date_collected")
        .first()
    )


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
    except (InvalidVersion, TypeError, ValueError, AttributeError):
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
    Return a SOURCE_REPO Package linked to ``package`` via PackageSet, or None.
    """
    if package is None:
        return None

    if package.package_content == PackageContentType.SOURCE_REPO:
        return package

    for package_set in package.package_sets.all():
        source = package_set.packages.filter(
            package_content=PackageContentType.SOURCE_REPO,
        ).first()
        if source:
            return source

    return None


def get_versionless_source_package(package):
    """Return a versionless SOURCE_REPO Package linked to ``package``, or None."""
    source = get_source_package(package)
    if source is None:
        return None
    if source.version == "":
        return source

    for package_set in package.package_sets.all():
        versionless = package_set.packages.filter(
            package_content=PackageContentType.SOURCE_REPO,
            version="",
        ).first()
        if versionless:
            return versionless
    return source if source.version == "" else None


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
    if source and source.version == version:
        return source
    return None


def resolve_source_package(base_package, latest_package=None):
    """
    Resolve versionless and versioned SOURCE_REPO Packages for ``base_package``.

    Both rows are created through purl2vcs ``get_source_package_and_add_to_package_set``:
    - versionless BASE_PACKAGE → fetchcode repo URL with version stripped
    - latest npm package → tag/commit matching

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
    - purl2vcs ``get_source_package_and_add_to_package_set`` for versionless
      SOURCE_REPO (fetchcode + strip version) and versioned SOURCE_REPO (tags)

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


def queue_health_metrics_scan(source_package, priority=100):
    """
    Queue ``scan_repo_health`` for ``source_package`` via ScannableURI.

    The pipeline itself runs on the hosted ScanCode.io instance; PurlDB only
    enqueues the job name. Reuses ``add_package_to_scan_queue``.
    Return the ScannableURI.
    """
    from minecode.models import ScannableURI

    pipelines = [HEALTH_METRICS_PIPELINE]
    add_package_to_scan_queue(
        source_package,
        pipelines=pipelines,
        priority=priority,
    )
    return ScannableURI.objects.filter(
        package=source_package,
        pipelines=pipelines,
    ).order_by("-id").first()


def _as_mapping(value):
    """Return ``value`` as a dict, parsing JSON strings and treating other types as empty."""
    if not value:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if isinstance(value, dict):
        return value
    return {}


def _merge_health_keys(target, source):
    """Copy health-related keys from ``source`` into ``target`` when target is missing them."""
    source = _as_mapping(source)
    for key in (
        "health_metrics",
        "metrics",
        "health_score",
        "npm_health_score",
        "package_health_version",
        "repository",
    ):
        incoming = source.get(key)
        if incoming in (None, "", {}, []):
            continue
        if target.get(key) in (None, "", {}, []):
            target[key] = incoming


def extract_health_scan_payload(project_extra_data=None, scan_data=None, summary_data=None):
    """
    Collect health metrics fields from a ScanCode.io webhook payload.

    SCIO ``scan_repo_health`` writes ``health_metrics`` / ``npm_health_score`` onto
    ``project.extra_data``. The same extra_data is also copied into
    ``results.headers[0].extra_data`` when the webhook includes scan results.
    """
    payload = {}
    _merge_health_keys(payload, project_extra_data)
    scan_data = _as_mapping(scan_data)
    headers = scan_data.get("headers") or []
    if headers and isinstance(headers[0], dict):
        _merge_health_keys(payload, headers[0].get("extra_data"))
    _merge_health_keys(payload, scan_data)
    _merge_health_keys(payload, summary_data)
    return payload


def write_package_health_metrics(
    package, project_extra_data=None, summary_data=None, scan_data=None
):
    """
    Persist PackageHealthMetrics for ``package`` from scan webhook payloads.

    Called from ``process_scan_results`` when the ScannableURI pipelines include
    ``scan_repo_health`` (executed on hosted ScanCode.io).

    Reads from ``project_extra_data`` and scan-result headers:
    - ``health_metrics`` or ``metrics`` (when a score is also present)
    - ``health_score`` or ``npm_health_score``
    - ``package_health_version`` (falls back to latest npm version in the package set)

    Return the created row, or None if the webhook did not include a real metrics payload.
    """
    payload = extract_health_scan_payload(
        project_extra_data=project_extra_data,
        scan_data=scan_data,
        summary_data=summary_data,
    )

    metrics = payload.get("health_metrics")
    score_value = payload.get("health_score")
    if score_value is None:
        score_value = payload.get("npm_health_score")
    if metrics is None and score_value is not None:
        metrics = payload.get("metrics")

    if not isinstance(metrics, dict) or not metrics:
        return None

    version = payload.get("package_health_version") or ""
    if not version:
        # Health metrics are keyed to the SOURCE_REPO but versioned by the npm
        # release they were collected for.
        for package_set in package.package_sets.all():
            npm_package = (
                package_set.packages.filter(type="npm")
                .exclude(version="")
                .order_by("-version")
                .first()
            )
            if npm_package and npm_package.version:
                version = npm_package.version
                break
    if not version:
        version = package.version or ""

    try:
        score = float(score_value)
    except (TypeError, ValueError):
        score = 0.0

    return PackageHealthMetrics.objects.create(
        package=package,
        scoring_model=get_or_create_scoring_model(),
        version=version,
        metrics=metrics,
        score=score,
        date_collected=timezone.now(),
    )


def resolve_health_request(purl):
    """
    Resolve a health-metrics request for a versionless npm ``purl``.

    Return a mapping with keys:
    - ``fresh_metrics``: PackageHealthMetrics or None
    - ``source_package``: SOURCE_REPO Package or None
    - ``latest_version``: str or None
    - ``scannable_uri``: ScannableURI or None (set when a job is queued)
    - ``error``: str or None
    """
    base_package = get_versionless_base_package(purl)

    if base_package is None:
        base_package, source_package, latest_version, error = collect_versionless_npm_package(
            purl
        )
        if error:
            return {
                "fresh_metrics": None,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": error,
            }
        if source_package is None:
            return {
                "fresh_metrics": None,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": "No source package found",
            }
    else:
        source_package, latest_version, error = ensure_source_package_for_base(
            base_package, purl
        )
        if error:
            return {
                "fresh_metrics": None,
                "source_package": None,
                "latest_version": latest_version,
                "scannable_uri": None,
                "error": error,
            }

    fresh_metrics = get_fresh_health_metrics(source_package, latest_version)
    if fresh_metrics:
        return {
            "fresh_metrics": fresh_metrics,
            "source_package": source_package,
            "latest_version": latest_version,
            "scannable_uri": None,
            "error": None,
        }

    scannable_uri = queue_health_metrics_scan(source_package)
    return {
        "fresh_metrics": None,
        "source_package": source_package,
        "latest_version": latest_version,
        "scannable_uri": scannable_uri,
        "error": None,
    }
