
==========
PurlDB
==========

PurlDB aka. ``Package URL Database`` is a database of software package metadata keyed by Package-URL
or purl that offers information and indentication services about software packages.

A purl or Package-URL is an attempt to standardize existing approaches to reliably identify and
locate software packages in general and Free and Open Source Softwarew (FOSS) packages in
particular.

A purl is a URL string used to identify and locate a software package in a mostly universal and
uniform way across programming languages, package managers, packaging conventions, tools, APIs and
databases.

Modern software is assembled from 100's or 1000's of FOSS packages: being able to catalog these,
normalize their metadata, track their versions, licenses and dependencies and being able to locate
and identify them is essential to healthy, sustainable and secure modern software development.


The PurlDB project consists of these main tools:


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

Collected packages can be used as reference for dependency resolution, as a reference knowledge base
for all package data, as a reference for vulnerable range resolution and more use cases. All of
these are important to support modern software development open source assembly.

