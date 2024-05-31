purldb-toolkit
==============

.. contents:: :local:
    :depth: 3

purldb-toolkit is a command line utility and library to use the PurlDB, its API and various related libraries.

The ``purlcli`` command acts as a client to the PurlDB REST API end point(s) to expose PURL services.
It serves as a tool, a library and an example of how to use the services programmatically.


Installation
------------

.. code-block:: console

    pip install purldb-toolkit


Usage
-----

Use this command to get basic help:

.. code-block:: console

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

``validate``: validate a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

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

.. code-block:: console

    purlcli validate --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --output <path/to/output.json>

*Sample output:*

.. code-block:: json

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

.. code-block:: console

    purlcli validate --file <path/to/output.txt> --output <path/to/output.json>

*Sample input.txt:*

.. code-block:: text

    pkg:npm/canonical-path@1.0.0
    pkg:nginx/nginx@0.8.9


Details
#######

``validate`` calls the ``validate/`` endpoint of the `purldb API <https://public.purldb.io/api/>`_.

See also https://public.purldb.io/api/docs/#/validate.


----


``versions``: collect package versions for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

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

.. code-block:: console

    purlcli versions --purl pkg:npm/canonical-path --purl pkg:nginx/nginx --output <path/to/output.json>

*Sample output:*

.. code-block:: json

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


Details
#######

``versions`` calls ``versions()`` from `fetchcode/package_versions.py`.

Version information is not needed in submitted PURLs and, if included, will be removed before processing.


----


``metadata``: collect package metadata for a PURL
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

.. code-block:: console

    purlcli metadata --purl pkg:openssl/openssl@3.0.6 --purl pkg:nginx/nginx@0.8.9 --purl pkg:gnu/glibc@2.38 --output <path/to/output.json>

*Sample output:*

.. code-block:: json

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


Details
#######

``metadata`` calls ``info()`` from `fetchcode/package.py`.

The intended output for each PURL type supported by the ``metadata`` command is

- an input PURL with a version: output the metadata for the input version
- an input PURL without a version: output a list of the metadata for all versions

The output of the various PURL types currently supported in `fetchcode/package.py` varies from type to type at the moment -- the underlying functions will be updated as needed so that all produce the intended output for input PURLs with and without a version.


----


``urls``: collect package URLs for a PURL
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

.. code-block:: console

    purlcli urls --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --purl pkg:rubygems/rails@7.0.0 --output <path/to/output.json>

*Sample output:*

.. code-block:: json

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

.. code-block:: console

    purlcli urls --purl pkg:npm/canonical-path@1.0.0 --purl pkg:nginx/nginx@0.8.9 --purl pkg:rubygems/rails@7.0.0 --output <path/to/output.json> --head

*Sample output:*

.. code-block:: json

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


Details
#######

None atm.
