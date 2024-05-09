.. _symbol_and_string_collection:

Symbol and String Collection
============================

The package indexing endpoint now also supports the symbol and string collection
pipeline and stores them in the ``extra_data`` field of the resource.

How it works
------------

When PurlDB receives an index request for a PURL via the ``/api/collect``
endpoint along with the symbol/string addon_pipeline, it fetches the archive
download_url and creates a package for the PURL with relevant metadata.
Thereafter, a scan job is scheduled which downloads the archive of the PURL
and runs the `scan_single_package <https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html#scan-single-package>`_
package pipeline. Scan job also runs the requested addon_pipelines.
Upon completion of the scan job, the package is updated with resource data along
with the ``source_symbols`` and ``source_strings`` in the ``extra_data`` field of
resources.

Currently PurlDB supports these addon_pipeline for symbol/string collection.

- ``collect_symbols_ctags``
- ``collect_strings_gettext``
- ``collect_symbols_tree_sitter``
- ``collect_symbols_pygments``

See the detailed tutorial on :ref:`tutorial_symbol_and_string_collection` in PurlDB.

.. line-block::

    To use these pipeline on ScanCode.io refer to  `Symbol and String Collection <https://scancodeio.readthedocs.io/en/latest/tutorial_web_ui_symbol_and_string_collection.html>`_.
    For more details on these plugins refer to `source-inspector <https://github.com/nexB/source-inspector/blob/main/README.rst>`_.
