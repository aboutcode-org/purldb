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
* ``libpq-dev``
*     If you are using Debian or Ubuntu : ``sudo apt install libpq-dev``
*     If you are using Fedora: ``sudo dnf install libpq-devel``

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

Populating Package Resource Data
--------------------------------

The Resources of Packages can be collected using the scan queue. By default, a
scan request will be created for each mapped Package.

The following environment variables will have to be set for the scan queue
commands to work:
::

    SCANCODEIO_URL=<ScanCode.io API URL>
    SCANCODEIO_API_KEY=<ScanCode.io API Key>

``matchcode-toolkit`` will also have to be installed in the same environment as
ScanCode.io. If running ScanCode.io in a virtual environment from a git
checkout, you can install ``matchcode-toolkit`` in editable mode:
::

    pip install -e <Path to purldb/matchcode-toolkit>

Otherwise, you can create a wheel from ``matchcode-toolkit`` and install it in
the ScanCode.io virutal environment or modify the ScanCode.io Dockerfile to
install the ``matchcode-toolkit`` wheel.

To build the ``matchcode-toolkit`` wheel:
::

    # From the matchcode-toolkit directory
    python setup.py bdist_wheel

The wheel ``matchcode_toolkit-0.0.1-py3-none-any.whl`` will be created in the
``matchcode-toolkit/dist/`` directory.

The scan queue is run using two commands:
::

    make request_scans

``request_scans`` will send a Package scan request to a configured ScanCode.io
instance. ScanCode.io will download, extract, and scan the files of the
requested Package.
::

    make process_scans

``process_scans`` will poll ScanCode.io for the status of the Package scans
requested by ``request_scans``. When a Package scan on ScanCode.io is ready,
``process_scans`` will use that data to create Resources and populate the
MatchCode directory fingerprint indices.

Package Resource data can also be gathered by running ClearCode, where Package
scan data from clearlydefined is collected and its results are used to create
Packages and Resources.
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

SPDX-License-Identifier: Apache-2.0 AND CC-BY-SA-4.0

purldb software is licensed under the Apache License version 2.0.

purldb data is licensed collectively under CC-BY-SA-4.0.

See https://www.apache.org/licenses/LICENSE-2.0 for the license text.

See https://creativecommons.org/licenses/by-sa/4.0/legalcode for the license text.

See https://github.com/nexB/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.
