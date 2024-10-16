Welcome to the PurlDB documentation!
====================================


`PurlDB <https://github.com/aboutcode-org/purldb>`__ aka. ``Package URL Database`` is a database of software package metadata keyed by a `Package-URL
or purl <https://github.com/package-url>`__ that offers information and indentication services about software packages.

A purl or Package-URL is an attempt to standardize existing approaches to reliably identify and
locate software packages in general and Free and Open Source Software (FOSS) packages in
particular.

A purl is a URL string used to identify and locate a software package in a mostly universal and
uniform way across programming languages, package managers, packaging conventions, tools, APIs and
databases.

Why PurlDB?
------------------

Modern software is assembled from 100's or 1000's of FOSS packages: being able to catalog these,
normalize their metadata, track their versions, licenses and dependencies and being able to locate
and identify them is essential to healthy, sustainable and secure modern software development.

This what PurlDB is all about and it offers:

- An active, continuously updated reference for FOSS packages origin, information and licensing,
  aka. open code knowledge base.
- A code matching capability to identify and find similar code to existing indexed FOSS code using
  this knowledge base.
- Additional utilities to help asses the quality and integrity of software packages as used in the
  software supply chain.


What can you do with PurlDB?
----------------------------

- Build a comprehensive open source software packages knowledge base. This includes the extensive
  scan of package code for origin, dependencies, embedded packages and licenses.

- Create advanced analysis for open source packages by collecting
  :ref:`symbols_and_strings`.

- Detect software supply chain issues by mapping package binaries to their corresponding source code
  and determining if there are possible discrepancies between sources and sources (such as with the
  XZ utils attack, or sources and binaries, where package may not report the exact source code
  used to build binaries with the :ref:`deploy_to_devel` mapping analysis.

- Access multiple services keyed by PURL, such as metadata, package versions, packages URLs, or
  dependencies.


What's in PurlDB?
-------------------

The PurlDB project consists of these main tools:

- PackageDB that is the database and reference model (based on ScanCode toolkit)
  that contains package data with purl (Package URLs) being a first class citizen and the primaty
  key to access information.

- MineCode that contains utilities to mine package repositories and populate the PackageDB

- MatchCode that contains utilities to index package metadata and resources for
  matching

- MatchCode.io that provides code package and files matching functionalities for codebases

- purldb-toolkit with its "purlcli" command line (CLI) utility and library to use the PurlDB, its
  API and various related libraries.

- ClearCode that contains utilities to mine Clearlydefined for package data.


These are designed to be used first for reference such that one can query for
packages by purl and validate purl existence.

Collected packages can be used as reference for dependency resolution, as a reference knowledge base
for all package data, as a reference for vulnerable range resolution and more use cases. All of
these are important to support modern software development open source assembly.


Getting Started
---------------

.. toctree::
   :maxdepth: 2

   getting-started/index

----

PurlDB
------

PurlDB is a database of packages, with package metadata and indexes for package
files and archives, and various API endpoints to get data about these packages
and match to other codebases.

.. toctree::
   :maxdepth: 2

   purldb/index

----

PurlDB toolkit
--------------

purldb-toolkit is command line utility and library to use the PurlDB, its API
and various related libraries.

.. toctree::
   :maxdepth: 2

   purldb-toolkit/index

----

Matchcode
---------

Matchcode has the functionalities to index archives, files and directories for purldb
packages and API endpoints to make matching available. A ScanCode.io pipeline for
matching is also present to match scanned codebases.

.. toctree::
   :maxdepth: 2

   matchcode/index


----

How-To Documents
----------------

How-To documents explain how to accomplish specific tasks.

.. toctree::
   :maxdepth: 2

   how-to-guides/index

----

See also
-------------

.. toctree::
   :maxdepth: 2

   license
   funding
   contributing
   testing
   changelog

----


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
