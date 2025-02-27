Changelog
=========

v6.0.0
---------

- Improve web template for API web page https://github.com/aboutcode-org/purldb/issues/132
- The API endpoints for ``approximate_directory_content_index``,
  ``approximate_directory_structure_index``, ``exact_file_index``,
  ``exact_package_archive_index``, ``cditems``, ``on_demand_queue`` have been
  removed.
- The `/api/collect/` and `/api/collect/index_packages/` API endpoints have been
  updated such that Package scan and processing requests made with purls with
  versions are processed ahead of those made with versionless purls.
  https://github.com/aboutcode-org/purldb/issues/502
- The `/api/scan_queue/` endpoint has been updated.
  `/api/scan_queue/get_next_download_url/` now returns a `webhook_url`, where
  the purldb scan worker will submit results. This is a URL to the
  `/api/scan_queue/index_package_scan/` endpoint.
  `/api/scan_queue/update_status/` is now an action on a ScannableURI.
  https://github.com/aboutcode-org/purldb/issues/504
- The packages collected via the `/api/collect/` endpoint can be ordered in an
  ascending or descending fashion on fields using the ``sort`` query parameter.
  This parameter takes in the same fields as ``sort`` from `/api/packages/`.
  https://github.com/aboutcode-org/purldb/issues/508
- Visitors and Mappers have been merged into a single module named ``miners``.
- Code is now formatted using ruff.
- purldb, matchcode, and other related projects have been updated to store,
  collect, and match code snippets. This is still in an early phase.
- Add FederatedCode support.
- Update queries when filtering resources by checksums to fix a performance issue.


v5.0.1
---------

- Update link references of ownership from nexB to aboutcode-org

v5.0.0
---------

- Add `/api/docs` Swagger API documentation for API endpoints.
- Add `/api/from_purl/purl2git` endpoint to get a git repo for a purl.
- Add `/api/to_purl/go` endpoint to get a purl from a golang import string or a package string in go.mod.
- Support indexing of PURLs listed in https://github.com/aboutcode-org/purldb/issues/326,
  https://github.com/aboutcode-org/purldb/issues/327, https://github.com/aboutcode-org/purldb/issues/328,
  https://github.com/aboutcode-org/purldb/issues/329 and https://github.com/aboutcode-org/purldb/issues/356.
- Support ``addon_pipelines`` for symbol and string collection in ``/api/collect`` endpoint. https://github.com/aboutcode-org/purldb/pull/393
- Store ``source_symbols`` and ``source_strings`` in ``extra_data`` field. https://github.com/aboutcode-org/purldb/pull/351


v3.0.0
-------

This is a major release with major API changes

- Add clearcode, matchcode, and matchcode-toolkit to purldb.
- Reorganize code such that purldb is a single Django app.
- support for new package repositories and ecosystems
- Add new matching capabilities for exact files
- Improve deployment with docker-compose
- Add new and improved scan queue
- Add a new matchcode-toolkit for matching packaged as a ScanCode plugin
- This is now using the latest version of ScanCode toolkit


v2.0.0
------

Initial release.
