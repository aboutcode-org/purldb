# `/api/health` — usage, flow, and scenarios

How to call the health metrics API, what happens end to end, which
scenarios are covered in this version, and what is still missing.

---

## Quick usage

```bash
# Request metrics for a versionless npm package
curl -s 'http://localhost:8006/api/health/?purl=pkg:npm/lodash'

# Scoped packages: URL-encode the @
curl -s 'http://localhost:8006/api/health/?purl=pkg:npm/%40angular/core'
```

| HTTP | Meaning | Client action |
| --- | --- | --- |
| **200** | Fresh metrics ready | Use the payload |
| **202** | Scan queued / in progress | Poll the same URL |
| **400** | Bad PURL, no source, or cannot resolve latest version | Fix input or stop |
| **500** | Failed to create/queue ScannableURI (should be rare) | Retry / check logs |

**200 body (ready):**

```json
{
  "purl": "pkg:npm/lodash",
  "source_purl": "pkg:github/lodash/lodash",
  "vcs_url": "https://github.com/lodash/lodash.git",
  "scoring_model": "npm-health-0.2",
  "score": 1.0,
  "commit_range": { "...": "..." },
  "run_start_date": "...",
  "run_end_date": "...",
  "metrics": { "...": "..." },
  "date_collected": "..."
}
```

**202 body (pending):**

```json
{
  "purl": "pkg:npm/lodash",
  "source_purl": "pkg:github/lodash/lodash",
  "status": "new"
}
```

`status` is the ScannableURI scan status (`new`, `submitted`, `in progress`,
`scanned`, `indexed`, …). Keep polling `GET /api/health/?purl=...` until 200
or a hard 400.

### Environment

| Variable | Default | Role |
| --- | --- | --- |
| `HEALTH_METRICS_MAX_AGE_DAYS` | `7` | Freshness window before re-queue |
| `SITE_URL` | — | Webhook base URL ScanCode.io calls back to (e.g. `http://host.docker.internal:8006` when SCIO is in Docker) |

Scan queue worker must authenticate as a user in the `scan_queue_workers`
group. PurlDB does **not** run `scan_repo_health` itself; ScanCode.io must.

---

## Assumptions (this version)

1. **Only versionless npm.** Rejects non-npm and versioned PURLs.
2. **Metrics hang on npm.** `PackageHealthMetrics.package` = versionless npm
   `BASE_PACKAGE`; `source_package` = versionless github `SOURCE_BASE_PACKAGE`.
   No `input_purl` column. API `purl` / `source_purl` map to those FKs.
3. **We scan the versionless source base package** (`scan_repo_health` only).
4. **Freshness + adopt.** Fresh row for this npm + latest version → 200.
   Else fresh row for the **same** `SOURCE_BASE_PACKAGE` (monorepo / shared
   source) → copy scan fields onto a new row for the requested npm (preserve
   original `date_collected`) → 200. Else queue / re-queue scan → 202.
5. **Latest npm version** is resolved at request time via fetchcode
   `package_versions.versions` and stored on the metrics row as `version`.
6. **Webhook `extra_data` shape is fixed** (no legacy key merge):

```json
{
  "vcs_url": "...",
  "scoring_model": "...",
  "score": 0.0,
  "commit_range": {},
  "run_start_date": "...",
  "run_end_date": "...",
  "metrics": {}
}
```

7. **Catalog ScoringModel** is always default
   `npmlargerecosystem` / `NPMMostUsed` / `0.1` (`catalog_scoring_model`).
   Scan-reported name stays on the CharField `scoring_model`.

---

## End-to-end flow (short)

1. Validate versionless npm `purl`.
2. Resolve/create npm `BASE_PACKAGE` + latest `SOURCE_ARCHIVE`; link in a
   `PackageSet`.
3. Resolve/create github `SOURCE_BASE_PACKAGE` (+ versioned `SOURCE_REPO`) via
   purl2vcs `get_source_package_and_add_to_package_set`.
4. `resolve_fresh_health_metrics` → own fresh row, or adopt from shared source.
5. Else stash `extra_data.health_npm_purl`, queue `scan_repo_health` on the
   source (reuse in-flight ScannableURI; create a **new** ScannableURI when the
   previous one finished or failed — do not reset, or ScanCode.io rejects
   duplicate project names).
6. Worker runs ScanCode.io; webhook → `process_scan_results` →
   `write_package_health_metrics` (health-only: skip fingerprint index).
7. Client polls until 200.

Main code: `HealthViewSet` (`packagedb/api.py`),
`resolve_health_request` / write / queue (`packagedb/package_health.py`),
`process_scan_results` (`minecode/tasks.py`).

---

## Scenario matrix (tested this version)

Automated: `PackageHealthMetricsAPITestCase` in `packagedb/tests/test_api.py`
(14 tests). Also exercised live against local `/api/health` and unit checks for
write / queue / webhook.

### Request validation → 400

| Scenario | Expected | Covered by |
| --- | --- | --- |
| Missing `purl` | 400 field required | live |
| Empty `purl` | 400 may not be blank | live |
| Invalid PURL string | 400 validation error | unit + live |
| Non-npm (`pypi`, `github`, …) | 400 only npm | unit + live |
| Versioned npm (`pkg:npm/lodash@4.17.21`) | 400 versionless only | unit + live |

### Collect / resolve

| Scenario | Expected | Covered by |
| --- | --- | --- |
| No BASE_PACKAGE yet | Create base + sources, queue scan → 202 | unit |
| Only versioned npm exists | Create BASE_PACKAGE, queue → 202 | unit |
| Scoped package (`@angular/core`) | Registry URL + sources correct → 202/200 | unit + live |
| Cannot resolve latest version (registry 404) | 400 “Could not resolve latest version” | unit + live (fixed: was uncaught HTTPError → 500) |
| No VCS / source found | 400 “No source package found” | unit |
| Package already known, metrics missing | Queue → 202, poll same status | unit + live |

### Cache / freshness / adopt

| Scenario | Expected | Covered by |
| --- | --- | --- |
| Fresh metrics for npm + latest version | 200, no new ScannableURI | unit + live (`lodash`) |
| Metrics older than `HEALTH_METRICS_MAX_AGE_DAYS` | Re-queue → 202 | unit |
| Stale + ScannableURI already `indexed` | Create **new** URI (`reindex_uri=True`), leave old indexed | unit |
| Previous URI in terminal failure (`failed` / `timeout` / `index failed`) | Create **new** URI (do not reset — avoids SCIO duplicate project name) | unit |
| Another npm shares same `SOURCE_BASE_PACKAGE` with fresh metrics | Adopt row → 200 (not bare indexed status) | unit + live (`lodash.debounce`) |
| Latest version changed (row exists for old version only) | Treat as miss → queue | unit (helpers) |
| Adopt preserves `date_collected` | Sibling stays inside freshness window | unit (helpers) |

### Queue / ScannableURI

| Scenario | Expected | Covered by |
| --- | --- | --- |
| First queue | Create ScannableURI `new`, pipelines=`[scan_repo_health]` | unit |
| Poll while `new` / in flight | Reuse same URI, do not reset | unit |
| Re-queue after `indexed` or terminal failure | Create new ScannableURI with new UUID | unit |
| Stash `health_npm_purl` on source | Webhook can resolve npm FK | code path + write tests |

### Webhook write (`write_package_health_metrics` / `process_scan_results`)

| Scenario | Expected | Covered by |
| --- | --- | --- |
| Full `extra_data` with non-empty `metrics` | Create row; health-only → `SCAN_INDEXED` | unit (helpers) |
| Missing or empty `metrics` | No row; health-only → `SCAN_INDEX_FAILED` + warning log | unit (helpers) |
| Invalid `score` | Store `0.0` | unit (helpers) |
| Resolve npm via `health_npm_purl` | Row.package = stashed npm | unit (helpers) |
| Resolve npm via package set fallback | Row.package = npm in set | unit (helpers) |

### Package / content types in a typical request

| Role | Example | `package_content` |
| --- | --- | --- |
| npm identity (metrics FK) | `pkg:npm/lodash` | `BASE_PACKAGE` |
| npm latest tarball | `pkg:npm/lodash@4.18.1` | `SOURCE_ARCHIVE` |
| github repo scanned | `pkg:github/lodash/lodash` | `SOURCE_BASE_PACKAGE` |
| github tag snapshot | `pkg:github/lodash/lodash@4.18.1` | `SOURCE_REPO` |

---

## Gaps and scenarios not fully covered yet

Use this list for follow-up work / next PR. Behavior below is either
untested, intentional limitation, or known soft spot.

### API / product gaps

1. **Non-npm ecosystems** — not accepted; no pypi/maven/cargo path.
2. **Versioned request PURLs** — always server-side “latest”; cannot ask for
   health of a specific historical npm version.
3. **No separate status URL** — clients must poll `/api/health/`; 202 does not
   include estimated wait or ScannableURI UUID.
4. **No auth / rate limit** on `/api/health` beyond whatever the site uses
   globally.
5. **No bulk endpoint** — one PURL per request (large SBOM loops are
   client-side).
6. **Response omits `version` and catalog ScoringModel** — clients cannot see
   which npm version the score was tied to without inspecting DB.
7. **Org renames / fork drift** — find_source may return a different org than
   SPDX `downloadLocation` (e.g. `facebook/react` vs `react/react`,
   `bitinn/node-fetch` vs `node-fetch/node-fetch`). Health follows find_source /
   fetchcode, not SPDX.
8. **Monorepo path vs root** — SPDX may store `/tree/.../packages/foo`; we
   scan the repo root `SOURCE_BASE_PACKAGE`. Same repo, different URL string.

### Pipeline / infrastructure gaps

9. **ScanCode.io `format_metrics_output` failures** — if SCIO finishes without
   writing `metrics` into `project.extra_data`, we mark `SCAN_INDEX_FAILED`.
   Client keeps getting 202 until something re-queues; no distinct “failed”
   HTTP status on `/api/health` (status string may show `failed` /
   `index failed` only while that ScannableURI is current).
10. **In-flight stuck scans** — `submitted` / `in progress` are never reset by
    a health request. A hung worker leaves clients polling 202 indefinitely
    until operator intervention or a new code path for timeout.
11. **Mixed pipelines** — if a ScannableURI ever had
    `scan_repo_health` plus other pipelines, indexing is not health-only.
    Health always creates pipelines=`[scan_repo_health]` only, so this is
    mainly a risk for manually created URIs.
12. **Webhook cannot resolve npm** — if `health_npm_purl` is missing and the
    package set has no npm package, write returns None → index failed.
13. **Docker networking** — wrong `SITE_URL` means webhook never reaches
    PurlDB; metrics never appear (looks like eternal 202).

### Data / concurrency soft spots

14. **Latest-version string sort** — we sort with univers npm version class;
    exotic pre-releases / non-semver tags could pick a surprising “latest”.
15. **Version on write** — webhook picks “first versioned npm in package set
    ordered by `-version`” (string order), which may disagree with the
    request-time fetchcode latest if the set is messy.
16. **Adopt ignores sibling’s `version` match** — any fresh metrics for the
    shared source are reused; we overwrite `version` with the requester’s
    latest. Intentional for monorepos, but scores are repo-level, not
    package-version-level.
17. **Concurrent first requests** for the same new PURL could race on
    package / ScannableURI creation (DB uniqueness usually collapses this;
    not load-tested).
18. **Multiple ScannableURIs** for same source + pipelines — queue logic uses
    `.order_by("-id").first()`; older duplicates are ignored.
19. **`HEALTH_METRICS_MAX_AGE_DAYS=0`** — every request re-queues (edge
    config); not explicitly tested.
20. **Private / missing npm packages** that 403 or time out — now mapped to
    “Could not resolve latest version” via broad `except`; message does not
    distinguish 404 vs network error.

### Tests still thin

21. No Django test that drives **full** `process_scan_results` health-only path
    through the API client (helpers cover write + status transitions).
22. No test for **in-progress** poll returning status `submitted` /
    `in progress` via HTTP.
23. No test that **failed** scan surfaces a clear client-visible error
    (today: keep polling; may see `status` reflecting failure until reset).
24. No test for collect failure `"Package does not exist on npmjs: ..."` when
    latest version resolves but registry tarball fetch fails.
25. find_source `MultipleObjectsReturned` on loose PURL match was fixed with
    exact `download_url` match; no dedicated health API regression test for
    monorepo multi-download_url packages beyond adopt.

---

## Main code locations

| Piece | Where |
| --- | --- |
| HTTP endpoint | `packagedb/api.py` — `HealthViewSet` |
| Validation | `packagedb/serializers.py` — `validate_versionless_npm_purl` |
| Response fields | `packagedb/serializers.py` — `PackageHealthMetricsSerializer` |
| Collect / resolve / queue / write | `packagedb/package_health.py` |
| Source packages | `purl2vcs/.../find_source_repo.py` |
| Models | `packagedb/models.py` — `PackageHealthMetrics`, `ScoringModel` |
| Webhook | `minecode/tasks.py` — `process_scan_results` |
| Settings | `purldb/settings.py` — `HEALTH_METRICS_MAX_AGE_DAYS` |
| Tests | `packagedb/tests/test_api.py` — `PackageHealthMetricsAPITestCase` |
