.. _healthycode:

===============================
Healthycode package health
===============================

PurlDB can collect project health metrics and a health score for a Package-URL
using `Healthycode <https://github.com/aboutcode-org/healthycode>`__.
Healthycode looks at Git history (commits, contributors, organizations, files)
and returns those metrics plus a score.

Call ``GET /api/health/``. Only versionless npm PURLs work for now, for
example ``pkg:npm/lodash``.

How it works
------------

1. You pass a versionless npm PURL.
2. PurlDB finds the latest npm version, the matching source repo PURL, and
   any stored ``PackageHealthMetrics``.
3. If those metrics are newer than ``HEALTH_METRICS_MAX_AGE_DAYS`` (default
   7 days), they are returned as HTTP 200.
4. Otherwise PurlDB queues ScanCode.io ``scan_repo_health`` on the
   versionless source package and returns HTTP 202. Call the same URL again
   until the scan finishes.

PurlDB does not run Healthycode itself. A ScanCode.io worker must run
``scan_repo_health`` and post results back on the scan queue.

See :ref:`healthycode_how_to` to call the API, :ref:`healthycode_metrics`
for field meanings, and :ref:`rest_api` for the endpoint listing.

Scoring
-------

``score`` is the probability that the repo is **unhealthy**: ``0.0`` is
healthy, ``1.0`` is unhealthy. It comes from a logistic regression over the
metrics. ``scoring_model`` names the model, for example ``npm-health-0.2``.

Details are in the
`Healthycode README <https://github.com/aboutcode-org/healthycode/blob/main/README.md>`_.

Settings
--------

``HEALTH_METRICS_MAX_AGE_DAYS``
    How long stored metrics stay fresh before a new scan is queued.
    Default: ``7``.

``REST_API_ENDPOINTS``
    Optional list of API prefixes to expose. A health-only instance can
    set this to ``health,scan_queue``.
