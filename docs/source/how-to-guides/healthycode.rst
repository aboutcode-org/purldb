.. _healthycode_how_to:

========================================
Collect package health with Healthycode
========================================

Request health metrics for an npm Package-URL.

.. note::
   You need PurlDB plus a ScanCode.io worker that can run
   ``scan_repo_health``. See :doc:`/getting-started/install-with-scio`.

Call the API
------------

Use a **versionless** npm PURL. Other ecosystems and versioned PURLs return
HTTP 400 with an ``error`` string.

.. code-block:: console

    curl -X GET "http://localhost:8001/api/health/?purl=pkg:npm/lodash&format=json"

.. code-block:: python

    import requests

    response = requests.get(
        "http://localhost:8001/api/health/",
        params={"purl": "pkg:npm/lodash", "format": "json"},
    )
    print(response.status_code, response.json())

Responses
---------

**200**: metrics newer than ``HEALTH_METRICS_MAX_AGE_DAYS`` are already
stored. The body has the score, commit range, and metrics. Field list:
:ref:`healthycode_metrics`.

**202**: nothing stored yet, or the data is stale. PurlDB queued
``scan_repo_health``. Repeat the same GET until you get 200. Large repos
can take a few minutes.

.. code-block:: json

    {
        "purl": "pkg:npm/lodash",
        "source_purl": "pkg:github/lodash/lodash",
        "status": "new"
    }

The OpenAPI UI at ``/api/docs/`` has the 200, 202, and error schemas.
