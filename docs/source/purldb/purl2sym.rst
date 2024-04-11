.. _purl2sym:

Purl2Sym
============

Purl2Sym collects the core package metadata along with symbols and strings
from source code and stores them in the ``extra_data`` field of the resource.

How it works
------------

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

source-inspector
------------------

source-inspector is a set of utilities to inspect and analyze source
code and collect interesting data using various tools such as code symbols and strings.
This is also a ScanCode-toolkit plugin.

Requirements
~~~~~~~~~~~~~

This utility is designed to work on Linux and POSIX OS with these utilities:

- xgettext that comes with GNU gettext.
- universal ctags, version 5.9 or higher, built with JSON support.

On Debian systems run this::

    sudo apt-get install universal-ctags gettext

On MacOS systems run this::

    brew install universal-ctags gettext

To get started:
~~~~~~~~~~~~~~~~

1. Clone this repo

2. Run::

    ./configure --dev
    source venv/bin/activate

3. Run tests with::

    pytest -vvs

4. Run a basic scan to collect symbols and display as YAML on screen::

    scancode --source-symbol tests/data/symbols_ctags/test3.cpp --yaml -

5. Run a basic scan to collect strings and display as YAML on screen::

    scancode --source-string tests/data/symbols_ctags/test3.cpp --yaml -

Pipeline in scancode.io
-------------------------

There is a ``collect_symbols`` pipeline in scancode.io to get symbols
using the ``source-inspector`` library for codebases.

See the `pipeline <https://github.com/nexB/scancode.io/blob/main/scanpipe/pipelines/collect_symbols.py>`_ for more details.

This is also available in the standard scancode.io pipelines used to scan packages
in purldb and symbols are stored in the ``extra_data`` field for all scanned resources
available in purldb.
