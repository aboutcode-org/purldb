purl2vcs
==========

purl2vcs is an add-on library working with the PurlDB to find the version control system (VCS) URL
of a package and detect the commit, and tags for a given version.

In the future, it will also find paths and branches, which is useful for monorepos.

Usage
-------

- First, import the main module: ``from purl2vcs import find_source_repo``

- To use the functions you first need to acquire some Package objects:
  Use the ``get_package_object_from_purl(package_url)`` passing a PURL string to get an object from
  the database

- To find the source repository of a Package, call `get_source_repo(package)`
  to will get a PackageURL object back.

- To generate all the source repository URLs of a Package, call `get_repo_urls(package)`.

- To convert a single source repo URLs to PURLs, call  ``convert_repo_url_to_purls``
- To convert a list of source repo URLs to PURLs, call  ``convert_repo_urls_to_purls``

- To find the commit or tags from a source repo PURL use ``get_tags_and_commits``

- The low level ``get_tags_and_commits`` is used in ``find_package_version_tag_and_commit`` to find
  the tag and commit of a given package ``version`` in a source repo PURL.


Installation
------------

Requirements
############

* install purldb dependencies
* `pip install purl2vcs`


Funding
-------

This project was funded through the NGI Assure Fund https://nlnet.nl/assure, a
fund established by NLnet https://nlnet.nl/ with financial support from the
European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 957073.

This project is also funded through grants from the Google Summer of Code
program, continuing support and sponsoring from nexB Inc. and generous
donations from multiple sponsors.


License
-------

Copyright (c) nexB Inc. and others. All rights reserved.

purldb is a trademark of nexB Inc.

SPDX-License-Identifier: Apache-2.0

pur2vcs is licensed under the Apache License version 2.0.

See https://www.apache.org/licenses/LICENSE-2.0 for the license text.

See https://creativecommons.org/licenses/by-sa/4.0/legalcode for the license text.

See https://github.com/nexB/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.
