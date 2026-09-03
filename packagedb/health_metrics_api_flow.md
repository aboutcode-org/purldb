# Package health metrics

This note is about how health metrics work in PurlDB today, how to call the API, and why we did things this way.

For now we only support npm, and the PURL you send must have no version (example: `pkg:npm/lodash`). PurlDB does not compute the score itself. ScanCode.io runs the `scan_repo_health` pipeline (GrimoireLab) and we store what comes back.

---

## How to use it

Call:

```
GET /api/health/?purl=pkg:npm/lodash
```

If you have no metrics yet, you get HTTP 202. Call the **same URL** again later. When metrics are ready you get HTTP 200.

Example:

```bash
curl -s 'http://127.0.0.1:8006/api/health/?purl=pkg:npm/lodash'
```

What you can get:

- **400** — bad PURL, not npm, or PURL has a version. Also 400 if we cannot find latest version, the package is not on npm, or we cannot find a source repo.
- **200** — we already have fresh metrics (not older than 7 days for the current latest npm version).
- **202** — we queued a scan, or the scan is still running.

PURL rules:

- OK: `pkg:npm/lodash`, scoped like `pkg:npm/%40angular/core`
- Not OK: `pkg:pypi/django`, `pkg:npm/lodash@4.17.21`, `not-a-purl`

We do not do extra checks on qualifiers or subpath in this version.

---

## When metrics are ready (HTTP 200)

This happens if we have a `PackageHealthMetrics` row on the versionless source repo package, for the current latest npm version, and `date_collected` is within 7 days.

```json
{
  "purl": "pkg:github/lodash/lodash",
  "version": "4.17.21",
  "metrics": {
    "total_commits": 260,
    "total_contributors": 33
  },
  "score": 8.5,
  "date_collected": "2026-09-03T17:40:00.123456Z"
}
```

- `purl` is the **source repo** (GitHub etc.), not the npm PURL you asked for.
- `version` is the npm version we collected for (latest at that time).
- `metrics` is the JSON from ScanCode.io / GrimoireLab.
- `score` is `npm_health_score` from ScanCode.io.
- `date_collected` is when we saved the row.

---

## When scan is not finished (HTTP 202)

```json
{
  "purl": "pkg:github/lodash/lodash",
  "status": "new"
}
```

Here `purl` is also the source repo package, because that is what we scan. `status` comes from `ScannableURI`:

- `new` — in the queue, worker did not take it yet
- `submitted` — worker took it
- `in progress` — pipeline is running
- `scanned` — ScanCode.io sent the webhook, but we did not finish saving yet
- `indexed` — save/index finished (next poll should be 200 if metrics were written)
- `failed` / `timeout` / `scan index failed` — something went wrong

If you call the same PURL again, we reuse the same `ScannableURI` (same uri, pipelines, package). The status just moves forward.

Error examples:

```json
{"error": "Could not resolve latest version for pkg:npm/lodash."}
{"error": "No source package found"}
```

For invalid `purl` you get a field error, like `{"purl": ["Only npm PackageURLs are supported."]}`.

---

## What happens from start to end

You send GET with the npm PURL. PurlDB first checks the PURL. Then it asks fetchcode for all versions and picks the latest (same idea as PackageWatch).

If we do not have packages yet, we create them:

1. A versionless npm **base package** (`version=""`, download URL like `https://registry.npmjs.org/lodash`).
2. The latest versioned npm package from the registry (source archive). We use the normal collect helpers. We do **not** queue `scan_single_package` / `fingerprint_codebase` for the tarball.
3. Source repo packages with purl2vcs, in the same package set: one **without version** (this is the one we scan and attach metrics to), and one **with the latest version** (tag/commit).

If we already have a base package, we just make sure source repo and latest version exist.

Then we look for health metrics on the versionless source repo for that latest npm version. If they are newer than 7 days, we return 200.

If not, we put the source repo on the scan queue with pipeline `scan_repo_health` and return 202.

The GET request **waits** for collect and finding the repo (npm, fetchcode, git tags). Only the ScanCode.io scan is in the background.

PurlDB does not run `scan_repo_health`. A scan worker calls `GET /api/scan_queue/get_next_download_url/`, gets the git URL, the pipeline name, and a webhook URL. It creates a ScanCode.io project, puts `scannable_uri_uuid` in `project.extra_data`, and runs `scan_repo_health`.

That pipeline needs one git URL. It runs grimoirelab-metrics, then puts `health_metrics`, `npm_health_score`, and `repository` on `project.extra_data`. The metrics file on disk is not sent to PurlDB. If extra_data is empty, we cannot store real metrics.

ScanCode.io then POSTs to `/api/scan_queue/index_package_scan/<key>/` with project, results, and summary. We set the ScannableURI to `scanned` and run `process_scan_results`.

If `PURLDB_ASYNC` is false, that runs in the same process. If it is true, the job goes to Redis and you need `python manage.py rqworker default`. If there is no worker, status stays `scanned` and metrics never get saved. Also: the process environment can override `.env`. We saw `PURLDB_ASYNC=True` on runserver even when `.env` said False.

`process_scan_results` always runs `index_package` first (files, fingerprints). For health scans the file list is often empty. Only if indexing does **not** fail, and the pipeline list has `scan_repo_health`, we call `write_package_health_metrics`.

We look for metrics in project extra_data (and also in results headers if they are there): `health_metrics` or `metrics`, and `health_score` or `npm_health_score`. Version comes from `package_health_version`, or from the latest npm package in the set. If there is no real metrics dict, we **do not** create a fake row. If we do create a row, we attach ScoringModel npm / health / 1.0.

After that, the same GET should return 200.

---

## What we store in the database

For one request we usually have:

- Base package: `pkg:npm/lodash`, content `base_package`, registry URL.
- Latest npm release: `pkg:npm/lodash@4.17.21`, content `source_archive`, tarball URL.
- Source repo without version: `pkg:github/lodash/lodash`, this is what we scan.
- Source repo with version/tag, also in the same PackageSet.

Health metrics point to the versionless source repo. The `version` field on the metrics row is the **npm** version, not the git tag.

`ScoringModel` is a small catalog: ecosystem, scoring_model, model_version. Unique together. These are normal text fields, not Django choices, so we can add new values later without a migration. For V1 we always use npm, health, 1.0. The FK on metrics can be null, and delete is PROTECT.

`PackageHealthMetrics` has package, scoring_model, version, metrics (JSON), score, date_collected. Unique on package + version + date_collected, so each collection is a **new** row. We take the newest one that is still within 7 days.

Migration file: `packagedb/migrations/0095_alter_package_package_content_scoringmodel_and_more.py`.

---

## Where the code is

- API: `packagedb/api.py` (`HealthViewSet`), URL in `purldb/urls.py` → `/api/health/`
- PURL check: `packagedb/serializers.py`
- Main logic: `packagedb/package_health.py`
- Models: `packagedb/models.py`
- Scan queue and webhook: `minecode/api.py`, `minecode/models.py`
- After webhook: `minecode/tasks.py` (`process_scan_results`)
- Queue insert: `minecode/model_utils.py`
- Finding git repo: `purl2vcs`
- Pipeline itself: ScanCode.io `scan_repo_health.py` (not in this repo)

There is still `GET /api/health/{uuid}/status/` in the code. Clients should ignore it and poll with the purl.

---

## What must be running

A 202 only means PurlDB queued the job. You still need:

- PurlDB server
- Postgres
- Redis, if `PURLDB_ASYNC=True`
- RQ worker in that case
- ScanCode.io and the purldb scan worker
- GrimoireLab (and OpenSearch) for the health pipeline

And ScanCode.io must copy metrics into `project.extra_data`, not only into a file.

---

## Decisions we already took

API:

- GET, not POST.
- One URL to start and to poll. No `poll_url`.
- 202 while waiting, 200 only when we have metrics.
- In 202, `purl` is the source repo. In 200, `purl` is also the source repo.
- No `from_cache` flag.
- We do not put `scannable_uri_uuid` in the main response.

Scope:

- npm only, no version on the request PURL.
- Always latest npm version from fetchcode, not a version from the client.
- Metrics hang on the versionless source repo. npm version is stored on the metrics row.
- Cache is 7 days for that package + that latest version. If latest on npm changes, we do not reuse the old version.
- We still ask fetchcode for latest on every GET, even when we return cache, so “latest” stays up to date.

Collect vs scan:

- Reuse existing collect and purl2vcs. Do not invent a second collect path.
- Do not queue the normal tarball scan for health. Only `scan_repo_health` on the git URL.
- That pipeline lives in ScanCode.io.

Saving:

- New row every time we collect, we do not overwrite the old one.
- No stub metrics if the webhook has no real data.
- ScoringModel ecosystem and scoring_model are free text.
- Base package uses registry metadata URL as `download_url` because that field is unique and version cannot be SQL NULL (we use empty string).

Status on 202 is the ScannableURI status (`new`, `submitted`, `scanned`, …), not a special health status like `pending` / `ready`.

---

## Next steps

- When we queue `scan_repo_health`, PurlDB should also send `ecosystem` and `project` to ScanCode.io (for example on the scan-queue payload or on project extra_data). Today we only send the git URL, pipelines, and `scannable_uri_uuid`.
- ScanCode.io `scan_repo_health` should pass those through to healthycode CLI as `ecosystem` and `project`.
- Keep them in extra_data on the way back, so when we write `PackageHealthMetrics` we can attach the matching `ScoringModel` (ecosystem + scoring_model=`project` + model version) instead of always hardcoding npm / health / 1.0 in PurlDB only.
- For `pkg:npm/lodash` that means CLI and DB both use ecosystem `npm` and project/scoring_model `health`.
- "npm_health_score" should only be "score" now
---

## Where we are now

Done:

- GET `/api/health/` for versionless npm.
- Create base package, latest npm package, and source repo packages with existing tools.
- Queue `scan_repo_health` on the versionless source repo.
- Same URL for polling, no `poll_url`, 202 purl is the source package.
- Webhook can write metrics from extra_data when indexing succeeds.
- 200 body: purl, version, metrics, score, date_collected.

This only works on a machine if the ScanCode.io worker is pulling the queue, the pipeline finishes and sets extra_data, and PurlDB actually runs `process_scan_results` (async false, or an RQ worker).
