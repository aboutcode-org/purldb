purldb-toolkit
==============

.. contents:: :local:
    :depth: 7



purldb-toolkit is command line utility and library to use the PurlDB, its API and various related libraries.

The ``purlcli`` command acts as a client to the PurlDB REST API end point(s) to expose PURL services.
It serves both as a tool, as a library and as an example on how to use the services programmatically.


Installation
------------

    pip install purldb-toolkit


Usage
-----

Use this command to get basic help::

    $ purlcli --help
    Usage: purlcli [OPTIONS] COMMAND [ARGS]...

      Return information from a PURL.

    Options:
      --help  Show this message and exit.

    Commands:
      metadata  Given one or more PURLs, for each PURL, return a mapping of...
      urls      Given one or more PURLs, for each PURL, return a list of all...
      validate  Check the syntax and upstream repo status of one or more PURLs.
      versions  Given one or more PURLs, return a list of all known versions...


And the following subcommands:

'validate' -- validate a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

    $ purlcli validate --help
    Usage: purlcli validate [OPTIONS]

      Check the syntax and upstream repo status of one or more PURLs.

    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write validation output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --help             Show this message and exit.

Examples
########

**Submit multiple PURLs using the command line:**

.. code-block:: none

    purlcli validate --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --output <path/to/output.json>

*Sample output:*

.. code-block:: console

    {
        "headers": [
            {
                "tool_name": "purlcli",
                "tool_version": "0.2.0",
                "options": {
                    "command": "validate",
                    "--purl": [
                        "pkg:npm/canonical-path@1.0.0",
                        "pkg:nginx/nginx@0.8.9"
                    ],
                    "--file": null,
                    "--output": "<path/to/output.json>"
                },
                "errors": [],
                "warnings": [
                    "'check_existence' is not supported for 'pkg:nginx/nginx@0.8.9'"
                ]
            }
        ],
        "packages": [
            {
                "purl": "pkg:npm/canonical-path@1.0.0",
                "valid": true,
                "exists": true,
                "message": "The provided Package URL is valid, and the package exists in the upstream repo."
            },
            {
                "purl": "pkg:nginx/nginx@0.8.9",
                "valid": true,
                "exists": null,
                "message": "The provided PackageURL is valid, but `check_existence` is not supported for this package type."
            }
        ]
    }


**Submit multiple PURLs using a .txt file:**

.. code-block:: none

    purlcli validate --file <path/to/output.txt> --output <path/to/output.json>

*Sample input.txt:*

.. code-block:: console

    pkg:npm/canonical-path@1.0.0
    pkg:nginx/nginx@0.8.9


Notes
#######

``validate`` calls the ``public.purldb.io/api/validate/`` endpoint.


----


'versions' -- collect package versions for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

    $ purlcli versions  --help
    Usage: purlcli versions [OPTIONS]

      Given one or more PURLs, return a list of all known versions for each PURL.

    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write versions output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --help             Show this message and exit.

Examples
########

**Submit multiple PURLs using the command line:**

.. code-block:: none

    purlcli versions --purl pkg:npm/canonical-path --purl pkg:nginx/nginx --output <path/to/output.json>

*Sample output:*

.. code-block:: console

    {
        "headers": [
            {
                "tool_name": "purlcli",
                "tool_version": "0.2.0",
                "options": {
                    "command": "versions",
                    "--purl": [
                        "pkg:npm/canonical-path",
                        "pkg:nginx/nginx"
                    ],
                    "--file": null,
                    "--output": "<path/to/output.json>"
                },
                "errors": [],
                "warnings": [
                    "'pkg:nginx/nginx' not supported with `versions` command"
                ]
            }
        ],
        "packages": [
            {
                "purl": "pkg:npm/canonical-path@0.0.1",
                "version": "0.0.1",
                "release_date": "2013-12-19"
            },
            {
                "purl": "pkg:npm/canonical-path@0.0.2",
                "version": "0.0.2",
                "release_date": "2013-12-19"
            },
            {
                "purl": "pkg:npm/canonical-path@1.0.0",
                "version": "1.0.0",
                "release_date": "2018-10-24"
            }
        ]
    }


Notes
#######

``versions`` calls ``versions()`` from `fetchcode/package_versions.py <https://github.com/nexB/fetchcode/blob/master/src/fetchcode/package_versions.py>`__.

Version information is not needed in submitted PURLs and, if included, will be removed before processing.


----


'metadata' -- collect package metadata for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    $ purlcli metadata --help
    Usage: purlcli metadata [OPTIONS]

      Given one or more PURLs, for each PURL, return a mapping of metadata fetched
      from the fetchcode package.py info() function.

    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write meta output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --help             Show this message and exit.

Examples
########

**Submit multiple PURLs using the command line:**

.. code-block:: none

    purlcli metadata --purl pkg:openssl/openssl@3.0.6 --purl pkg:nginx/nginx@0.8.9 --purl pkg:gnu/glibc@2.38 --output <path/to/output.json>

*Sample output:*

.. code-block:: console

    {
        "headers": [
            {
                "tool_name": "purlcli",
                "tool_version": "0.2.0",
                "options": {
                    "command": "metadata",
                    "--purl": [
                        "pkg:openssl/openssl@3.0.6",
                        "pkg:nginx/nginx@0.8.9",
                        "pkg:gnu/glibc@2.38"
                    ],
                    "--file": null,
                    "--output": "<path/to/output.json>"
                },
                "errors": [],
                "warnings": [
                    "'check_existence' is not supported for 'pkg:openssl/openssl@3.0.6'",
                    "'pkg:nginx/nginx@0.8.9' not supported with `metadata` command",
                    "'check_existence' is not supported for 'pkg:gnu/glibc@2.38'"
                ]
            }
        ],
        "packages": [
            {
                "purl": "pkg:openssl/openssl@3.0.6",
                "type": "openssl",
                "namespace": null,
                "name": "openssl",
                "version": "3.0.6",
                "qualifiers": {},
                "subpath": null,
                "primary_language": "C",
                "description": null,
                "release_date": "2022-10-11T12:39:09",
                "parties": [],
                "keywords": [],
                "homepage_url": "https://www.openssl.org",
                "download_url": "https://github.com/openssl/openssl/archive/refs/tags/openssl-3.0.6.tar.gz",
                "api_url": "https://api.github.com/repos/openssl/openssl",
                "size": null,
                "sha1": null,
                "md5": null,
                "sha256": null,
                "sha512": null,
                "bug_tracking_url": "https://github.com/openssl/openssl/issues",
                "code_view_url": "https://github.com/openssl/openssl",
                "vcs_url": "git://github.com/openssl/openssl.git",
                "copyright": null,
                "license_expression": null,
                "declared_license": "Apache-2.0",
                "notice_text": null,
                "root_path": null,
                "dependencies": [],
                "contains_source_code": null,
                "source_packages": [],
                "repository_homepage_url": null,
                "repository_download_url": null,
                "api_data_url": null
            },
            {
                "purl": "pkg:gnu/glibc@2.38",
                "type": "gnu",
                "namespace": null,
                "name": "glibc",
                "version": "2.38",
                "qualifiers": {},
                "subpath": null,
                "primary_language": null,
                "description": null,
                "release_date": "2023-07-31T17:34:00",
                "parties": [],
                "keywords": [],
                "homepage_url": "https://ftp.gnu.org/pub/gnu/glibc/",
                "download_url": "https://ftp.gnu.org/pub/gnu/glibc/glibc-2.38.tar.gz",
                "api_url": null,
                "size": null,
                "sha1": null,
                "md5": null,
                "sha256": null,
                "sha512": null,
                "bug_tracking_url": null,
                "code_view_url": null,
                "vcs_url": null,
                "copyright": null,
                "license_expression": null,
                "declared_license": null,
                "notice_text": null,
                "root_path": null,
                "dependencies": [],
                "contains_source_code": null,
                "source_packages": [],
                "repository_homepage_url": null,
                "repository_download_url": null,
                "api_data_url": null
            }
        ]
    }


Notes
#######

``metadata`` calls ``info()`` from `fetchcode/package.py <https://github.com/nexB/fetchcode/blob/master/src/fetchcode/package.py>`__.

The intended output for each PURL type supported by the ``metadata`` command is

- an input PURL with a version: output the metadata for the input version
- an input PURL with no version: output a list of the metadata for all versions

The output of the various PURL types currently supported in `fetchcode/package.py <https://github.com/nexB/fetchcode/blob/master/src/fetchcode/package.py>`__ varies from type to type at the moment -- the underlying functions will be updated as needed so that all produce the intended output for input PURLs with and without a version.


----


'urls' -- collect package URLs for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    $ purlcli urls --help
    Usage: purlcli urls [OPTIONS]

      Given one or more PURLs, for each PURL, return a list of all known URLs
      fetched from the packageurl-python purl2url.py code.

    Options:
      --purl TEXT        PackageURL or PURL.
      --output FILENAME  Write urls output as JSON to FILE.  [required]
      --file FILENAME    Read a list of PURLs from a FILE, one per line.
      --head             Validate each URL's existence with a head request.
      --help             Show this message and exit.

Examples
########

**Submit multiple PURLs using the command line:**

.. code-block:: none

    purlcli urls --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --purl pkg:rubygems/rails@7.0.0 --output <path/to/output.json>

*Sample output:*

.. code-block:: console

    {
        "headers": [
            {
                "tool_name": "purlcli",
                "tool_version": "0.2.0",
                "options": {
                    "command": "urls",
                    "--purl": [
                        "pkg:npm/canonical-path@1.0.0",
                        "pkg:nginx/nginx@0.8.9",
                        "pkg:rubygems/rails@7.0.0"
                    ],
                    "--file": null,
                    "--output": "<path/to/output.json>"
                },
                "errors": [],
                "warnings": [
                    "'pkg:nginx/nginx@0.8.9' not supported with `urls` command",
                    "'check_existence' is not supported for 'pkg:rubygems/rails@7.0.0'"
                ]
            }
        ],
        "packages": [
            {
                "purl": "pkg:npm/canonical-path@1.0.0",
                "download_url": "http://registry.npmjs.org/canonical-path/-/canonical-path-1.0.0.tgz",
                "inferred_urls": [
                    "https://www.npmjs.com/package/canonical-path/v/1.0.0",
                    "http://registry.npmjs.org/canonical-path/-/canonical-path-1.0.0.tgz"
                ],
                "repository_download_url": null,
                "repository_homepage_url": "https://www.npmjs.com/package/canonical-path/v/1.0.0"
            },
            {
                "purl": "pkg:rubygems/rails@7.0.0",
                "download_url": "https://rubygems.org/downloads/rails-7.0.0.gem",
                "inferred_urls": [
                    "https://rubygems.org/gems/rails/versions/7.0.0",
                    "https://rubygems.org/downloads/rails-7.0.0.gem"
                ],
                "repository_download_url": null,
                "repository_homepage_url": "https://rubygems.org/gems/rails/versions/7.0.0"
            }
        ]
    }


**Include head and get requests:**

``--head``

.. code-block:: none

    purlcli urls --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --purl pkg:rubygems/rails@7.0.0 --output <path/to/output.json> --head

*Sample output:*

.. code-block:: console

    {
        "headers": [
            {
                "tool_name": "purlcli",
                "tool_version": "0.2.0",
                "options": {
                    "command": "urls",
                    "--purl": [
                        "pkg:npm/canonical-path@1.0.0",
                        "pkg:nginx/nginx@0.8.9",
                        "pkg:rubygems/rails@7.0.0"
                    ],
                    "--file": null,
                    "--head": true,
                    "--output": "<stdout>"
                },
                "errors": [],
                "warnings": [
                    "'pkg:nginx/nginx@0.8.9' not supported with `urls` command",
                    "'check_existence' is not supported for 'pkg:rubygems/rails@7.0.0'"
                ]
            }
        ],
        "packages": [
            {
                "purl": "pkg:npm/canonical-path@1.0.0",
                "download_url": {
                    "url": "http://registry.npmjs.org/canonical-path/-/canonical-path-1.0.0.tgz",
                    "get_request_status_code": 200,
                    "head_request_status_code": 301
                },
                "inferred_urls": [
                    {
                        "url": "https://www.npmjs.com/package/canonical-path/v/1.0.0",
                        "get_request_status_code": 200,
                        "head_request_status_code": 200
                    },
                    {
                        "url": "http://registry.npmjs.org/canonical-path/-/canonical-path-1.0.0.tgz",
                        "get_request_status_code": 200,
                        "head_request_status_code": 301
                    }
                ],
                "repository_download_url": {
                    "url": null,
                    "get_request_status_code": "N/A",
                    "head_request_status_code": "N/A"
                },
                "repository_homepage_url": {
                    "url": "https://www.npmjs.com/package/canonical-path/v/1.0.0",
                    "get_request_status_code": 200,
                    "head_request_status_code": 200
                }
            },
            {
                "purl": "pkg:rubygems/rails@7.0.0",
                "download_url": {
                    "url": "https://rubygems.org/downloads/rails-7.0.0.gem",
                    "get_request_status_code": 200,
                    "head_request_status_code": 200
                },
                "inferred_urls": [
                    {
                        "url": "https://rubygems.org/gems/rails/versions/7.0.0",
                        "get_request_status_code": 200,
                        "head_request_status_code": 200
                    },
                    {
                        "url": "https://rubygems.org/downloads/rails-7.0.0.gem",
                        "get_request_status_code": 200,
                        "head_request_status_code": 200
                    }
                ],
                "repository_download_url": {
                    "url": null,
                    "get_request_status_code": "N/A",
                    "head_request_status_code": "N/A"
                },
                "repository_homepage_url": {
                    "url": "https://rubygems.org/gems/rails/versions/7.0.0",
                    "get_request_status_code": 200,
                    "head_request_status_code": 200
                }
            }
        ]
    }


Notes
#######

- None atm.


Testing
-------

Run all purldb tests:

.. code-block:: none

    make test

Run all purlcli non-live tests (i.e., no live network calls):

.. code-block:: none

    DJANGO_SETTINGS_MODULE=purldb_project.settings pytest -vvs purldb-toolkit/tests/test_purlcli.py

Run all purlcli live tests (i.e., check actual API endpoints etc.)

.. code-block:: none

    DJANGO_SETTINGS_MODULE=purldb_project.settings pytest -vvs purldb-toolkit/tests/test_purlcli_live.py --run_live_fetch


Funding
-------

This project was funded through the NGI Assure Fund https://nlnet.nl/assure, a
fund established by NLnet https://nlnet.nl/ with financial support from the
European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 957073.

This project is also funded through grants from the Google Summer of Code
program, continuing support and sponsoring from nexB Inc. and generous
donations from multiple sponsors.


License
-------

Copyright (c) nexB Inc. and others. All rights reserved.

purldb is a trademark of nexB Inc.

SPDX-License-Identifier: Apache-2.0 AND CC-BY-SA-4.0

purldb software is licensed under the Apache License version 2.0.

purldb data is licensed collectively under CC-BY-SA-4.0.

See https://www.apache.org/licenses/LICENSE-2.0 for the license text.

See https://creativecommons.org/licenses/by-sa/4.0/legalcode for the license text.

See https://github.com/nexB/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.
