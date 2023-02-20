The purldb
==========
This repo consists of four main tools:

- PackageDB that is the reference model (based on ScanCode toolkit)
  that contains package data with purl (Package URLs) being a first
  class citizen.
- MineCode that contains utilities to mine package repositories
- MatchCode that contains utilities to index package metadata and resources for
  matching
- ClearCode that contains utilities to mine Clearlydefined for package data

These are designed to be used first for reference such that one can query for
packages by purl and validate purl existence.

In the future, the collected packages will be used as reference for dependency
resolution, as a reference knowledge base for all package data, as a reference
for vulnerable range resolution and more.


Installation
------------
Requirements
############
* Debian-based Linux distribution
* Python 3.8 or later
* Postgres 13
* git
* scancode-toolkit runtime dependencies (https://scancode-toolkit.readthedocs.io/en/stable/getting-started/install.html#install-prerequisites)

Once the prerequisites have been installed, set up PurlDB with the following commands:
::

    git clone https://github.com/nexb/purldb
    cd purldb
    make dev
    make envfile
    make postgres

Once PurlDB and the database has been set up, run tests to ensure functionality:
::

    make test


Usage
-----
Start the PurlDB server by running:
::

    make run

To start visiting upstream package repositories for package metadata:
::

    make run_visit

To populate the PackageDB using visited package metadata:
::

    make run_map

If you have an empty PackageDB without Package and Package Resource information,
ClearCode should be run for a while so it can populate the PackageDB
with Package and Package Resource information from clearlydefined.
::

    make clearsync

After some ClearlyDefined harvests and definitions have been obtained, run
``clearindex`` to create Packages and Resources from the harvests and
definitions.
::

    make clearindex

The Package and Package Resource information will be used to create the matching indices.

Once the PackageDB has been populated, run the following command to create the
matching indices from the collected Package data:
::

    make index_packages


API Endpoints
-------------

* ``api/packages``

  * Contains all of the Packages stored in the PackageDB

* ``api/resources``

  * Contains all of the Resources stored in the PackageDB

* ``api/cditems``

  * Contains the visited ClearlyDefined harvests or definitions

* ``api/approximate_directory_content_index``

  * Contains the directory content fingerprints for Packages with Resources
  * Used to check if a directory and the files under it is from a known Package using the SHA1 values of the files

* ``api/approximate_directory_structure_index``

  * Contains the directory structure fingerprints for Packages with Resources
  * Used to check if a directory and the files under it is from a known Package using the name of the files

* ``api/exact_file_index``

  * Contains the SHA1 values of Package Resources
  * Used to check the SHA1 values of files from a scan to see what Packages also has that file

* ``api/exact_package_archive_index``

  * Contains the SHA1 values of Package archives
  * Used to check the SHA1 values of archives from a scan to determine if they are known Packages


License
-------

Copyright (c) nexB Inc. and others. All rights reserved.

purldb is a trademark of nexB Inc.

SPDX-License-Identifier: Apache-2.0 AND CC-BY-SA-4.0

purldb software is licensed under the Apache License version 2.0.

purldb data is licensed collectively under CC-BY-SA-4.0.

See https://www.apache.org/licenses/LICENSE-2.0 for the license text.

See https://creativecommons.org/licenses/by-sa/4.0/legalcode for the license text.

See https://github.com/nexB/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.
