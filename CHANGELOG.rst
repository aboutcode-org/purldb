Changelog
=========

Next Release
----------------

- Add `/api/from_purl/purl2git` endpoint to get a git repo for a purl.
- Add `/api/to_purl/go` endpoint to get a purl from a golang import string or a package string in go.mod.


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
