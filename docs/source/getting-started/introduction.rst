:orphan:

Introduction
=============

What can you do with PurlDB?
------------------------------

- Build a comprehensive open source software packages knowledge base. This includes the extensive
  scan of the code  of packages for origin, dependencies, embedded packages and licenses.

- Create advanced analysis for open source packages by collecting
  :ref:`symbols_and_strings`.

- Detect software supply chain issues by mapping package binaries to their corresponding source code
  and determining if there are possible discrepancies between sources and binaries (such as with the
  XZ utils attack, or sources and binaries, where package may not report the exact source code
  used to build binaries with the :ref:`deploy_to_devel` mapping analysis.

- Access multiple services keyed by PURL, such as metadata, package versions, packages URLs, or
  dependencies.


What tools are available in PurlDB?
-------------------------------------

The PurlDB project consists of these main tools:

- PackageDB that is the database and reference model (based on ScanCode toolkit)
  that contains package data with PURL (Package URLs) being a first class citizen and the primary
  key to access information.

- MineCode that contains utilities to mine package repositories and populate the PackageDB

- MatchCode that contains utilities to index package metadata and resources for
  matching

- MatchCode.io that provides code package and files matching functionalities for codebases

- purldb-toolkit with its "purlcli" command line (CLI) utility and library to use the PurlDB, its
  API and various related libraries.

- ClearCode that contains utilities to mine Clearlydefined for package data.


