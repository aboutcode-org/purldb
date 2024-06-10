The purldb
==========
This repo consists of these main tools:

- PackageDB that is the reference model (based on ScanCode toolkit)
  that contains package data with purl (Package URLs) being a first
  class citizen.
- MineCode that contains utilities to mine package repositories
- MatchCode that contains utilities to index package metadata and resources for
  matching
- MatchCode.io that provides package matching functionalities for codebases
- ClearCode that contains utilities to mine Clearlydefined for package data
- purldb-toolkit CLI utility and library to use the PurlDB, its API and various
  related libraries.

These are designed to be used first for reference such that one can query for
packages by purl and validate purl existence.

In the future, the collected packages will be used as reference for dependency
resolution, as a reference knowledge base for all package data, as a reference
for vulnerable range resolution and more.

Documentation
-------------

See https://aboutcode.readthedocs.io/projects/PURLdb/en/latest/ for PurlDB
documentation.
