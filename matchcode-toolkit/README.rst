MatchCode toolkit
=================

MatchCode toolkit is a Python library that provides the directory fingerprinting
functionality for `ScanCode toolkit <https://github.com/aboutcode-org/scancode-toolkit>`_
and `ScanCode.io <https://github.com/aboutcode-org/scancode.io>`_ by implementing the
HaloHash algorithm and using it in ScanCode toolkit and ScanCode.io plugins and
pipelines.


Installation
------------

MatchCode toolkit must be installed in the same environment as ScanCode toolkit
or ScanCode.io.

From PyPI:
::

  pip install matchcode-toolkit

A checkout of this repo can also be installed into an environment using pip's
``--editable`` option,
::

  # Activate the virtual environment you want to install MatchCode-toolkit into,
  # change directories to the ``matchcode-toolkit`` directory
  pip install --editable .

or built into a wheel and then installed:
::

  pip install flot
  flot --wheel --sdist # The built wheel will be in the dist/ directory
  pip install matchcode_toolkit-*-py3-none-any.whl


Usage
-----

MatchCode toolkit provides the ``--fingerprint`` option for ScanCode toolkit.
This is a post-scan plugin that adds the fields
``directory_content_fingerprint`` and ``directory_structure_fingerprint`` to
Resources and computes those values for directories.
::

  scancode --info --fingerprint <scan target location> --json-pp <output location>


MatchCode toolkit provides the ``scan_and_fingerprint_package`` pipeline for
ScanCode.io. This is the same as the ``scan_single_package`` pipeline, but has the
added step of computing fingerprints for directories.

.. note::

    MatchCode toolkit has moved to its own repo at https://github.com/aboutcode-org/matchcode-toolkit
    from its previous location https://github.com/aboutcode-org/purldb/tree/main/matchcode-toolkit
