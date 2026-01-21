PurlDB Documentation
====================

PurlDB provides tools to create and update a database of package metadata keyed by 
PURL (Package URL) and an API for the PURL data. PurlDB is an `AboutCode project <https://aboutcode.org>`_.

Details of the Package URL specification are available `here <https://github.com/package-url>`_.

PurlDB offers: 

- An active, continuously updated reference for FOSS packages origin, information and licensing,
  aka. open code knowledge base.
- A code matching capability to identify and find similar code to existing indexed FOSS code using
  this knowledge base.
- Additional utilities to help asses the quality and integrity of software packages as used in the
  software supply chain.

Documentation overview
~~~~~~~~~~~~~~~~~~~~~~

The overview below outlines how the documentation is structured
to help you know where to look for certain things.

.. rst-class:: clearfix row

.. rst-class:: column column2 top-left

Getting started
~~~~~~~~~~~~~~~~~~~~~~

Start here if you are new to PurlDB.

- :doc:`getting-started/index`

.. rst-class:: column column2 top-right

How-To
~~~~~~~~~~~~~~~~~~~~~~

Learn via practical step-by-step guides.

- :doc:`how-to-guides/index`

.. rst-class:: column column2 bottom-left

Reference Docs
~~~~~~~~~~~~~~~~~~

Reference documentation for PurlDB features and customizations.

- :doc:`matchcode/index`

.. rst-class:: column column2 bottom-right

Explanations
~~~~~~~~~~~~~~~~~~

Consult the reference to understand PurlDB concepts.

- :doc:`purldb/index`

.. rst-class:: row clearfix

Misc
~~~~~~~~~~~~~~~

- :doc:`license`
- :doc:`funding`
- :doc:`contributing`
- :doc:`testing`
- :doc:`changelog`

.. include:: improve-docs.rst


Indices and tables
==================

* :doc:`genindex`
* :doc:`search`

.. toctree::
    :maxdepth: 2
    :hidden:

What can you do with PurlDB?
============================

- Build a comprehensive open source software packages knowledge base. This includes the extensive
  scan of package code for origin, dependencies, embedded packages and licenses.

- Create advanced analysis for open source packages by collecting
  :doc:`symbols_and_strings`.

- Detect software supply chain issues by mapping package binaries to their corresponding source code
  and determining if there are possible discrepancies between sources and binaries (such as with the
  XZ utils attack, or sources and binaries, where package may not report the exact source code
  used to build binaries with the :doc:`deploy_to_devel` mapping analysis.

- Access multiple services keyed by PURL, such as metadata, package versions, packages URLs, or
  dependencies.

What's in PurlDB?
=================

The PurlDB project consists of these main tools:

- PackageDB that is the database and reference model (based on ScanCode toolkit)
  that contains package data with PURL (Package URLs) being a first class citizen and the primaty
  key to access information.

- MineCode that contains utilities to mine package repositories and populate the PackageDB

- MatchCode that contains utilities to index package metadata and resources for
  matching

- MatchCode.io that provides code package and files matching functionalities for codebases

- purldb-toolkit with its "purlcli" command line (CLI) utility and library to use the PurlDB, its
  API and various related libraries.

- ClearCode that contains utilities to mine Clearlydefined for package data.

