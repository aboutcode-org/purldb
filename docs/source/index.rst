PurlDB Documentation
====================

PurlDB provides tools to create and update a database of package metadata keyed by
PURL (Package URL) and an API for the PURL data. PurlDB is an `AboutCode project <https://aboutcode.org>`_.

PurlDB offers:

- An active, continuously updated reference for FOSS packages origin, information and licensing,
  aka. open code knowledge base.
- A code matching capability to identify and find similar code to existing indexed FOSS code using
  this knowledge base.
- Additional utilities to help assess the quality and integrity of software packages as used in the
  software supply chain.

Details of the Package URL specification are available `here <https://github.com/package-url>`_.

PURL is the `official ECMA-427 standard <https://tc54.org/purl/>`_.


Documentation overview
~~~~~~~~~~~~~~~~~~~~~~

The overview below outlines how the documentation is structured
to help you know where to look for certain things.

.. rst-class:: clearfix row

.. rst-class:: column column2 top-left

Getting started
~~~~~~~~~~~~~~~~~~~~~~

Start here if you are new to PurlDB.

- :doc:`getting-started/introduction`
- :doc:`getting-started/install`
- :doc:`getting-started/install-with-scio`
- :doc:`getting-started/tasks`
- :doc:`getting-started/usage`

.. rst-class:: column column2 top-right

Tutorials
~~~~~~~~~~~~~~~~~~~~~~

Learn via practical step-by-step guides.

- :doc:`how-to-guides/index`
- :doc:`how-to-guides/installation`
- :doc:`how-to-guides/matchcode`
- :doc:`how-to-guides/deploy_to_devel`
- :doc:`how-to-guides/purl_watch_how_to`
- :doc:`how-to-guides/symbols_and_strings`

.. rst-class:: column column2 bottom-left

Code Matching Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reference documentation for MatchCode features and customizations.

- :doc:`matchcode/index`
- :doc:`matchcode/matchcode-pipeline`

.. rst-class:: column column2 bottom-right

Explanations
~~~~~~~~~~~~~~~~~~

Consult the reference to understand PurlDB concepts.

- :doc:`purldb/purl_watch`
- :doc:`purldb/rest_api`
- :doc:`purldb/symbol_and_string_collection`

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

* :ref:`genindex`
* :ref:`search`

.. toctree::
    :maxdepth: 2
    :hidden:

    getting-started/index
    matchcode/index
    how-to-guides/index
    purldb/index
    contributing
    changelog
    license
    testing


