.. _purl2sym:

Purl2Sym
============

Purl2Sym collects the core package metadata along with symbols and strings
from source code and stores them in the ``extra_data`` field of the resource.

How it works
^^^^^^^^^^^^

When PurlDB receives an index request for a PURL via the ``/api/collect``
endpoint, it fetches the archive download_url and creates a package for
the PURL with relevant metadata. Thereafter, a scan job is scheduled which
downloads the archive of the PURL and runs the `scan_single_package <https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html#scan-single-package>`_
package pipeline. Thereafter, the scan job also runs the two addon pipelines:
`collect_symbols <https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html#collect-codebase-symbols-addon>`_
and `collect_source_strings <https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html#collect-source-strings-addon>`_
for symbol and string collection respectively. Upon completion of the scan
job, the package is updated with resource data along with the ``source_symbols``
and ``source_strings`` in the ``extra_data`` field of resources.
