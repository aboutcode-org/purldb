Changelog
=========

Next Release
----------------

- Add `/api/from_purl/purl2git` endpoint to get a git repo for a purl.
- Add `/api/to_purl/go` endpoint to get a purl from a golang import string or a package string in go.mod.
- Support indexing of PURLs listed in https://github.com/nexB/purldb/issues/326,
  https://github.com/nexB/purldb/issues/327, https://github.com/nexB/purldb/issues/328,
  https://github.com/nexB/purldb/issues/329 and https://github.com/nexB/purldb/issues/356.
- Support ``addon_pipelines`` for symbol and string collection in ``/api/collect`` endpoint. https://github.com/nexB/purldb/pull/393 
- Store ``source_symbols`` and ``source_strings`` in ``extra_data`` field. https://github.com/nexB/purldb/pull/351


v4.0.0
------------

- Add `/api/docs` Swagger API documentation for API endpoints.

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
