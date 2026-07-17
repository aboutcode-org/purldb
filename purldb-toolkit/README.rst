purldb-toolkit
==============

.. contents:: :local:
    :depth: 3

purldb-toolkit is a command line utility and library to use the PurlDB, its API and various related libraries.

purldb-toolkit exposes the ``purlcli`` command that acts as a client to the PURL libraries,
the PurlDB and MatchCode REST API and exposes various PURL-based services.

purldb-toolkit serves as a tool, a library and an example of how to use the services programmatically.

.. note::

    purldb-toolkit has moved to its own repo at https://github.com/aboutcode-org/purldb-toolkit
    from its previous location at https://github.com/aboutcode-org/purldb/tree/main/purldb-toolkit

Installation
------------

.. code-block:: console

    pip install purldb-toolkit


Usage
-----

The purlcli command exposes multiple subcommands. Run this to command to get basic help:

.. code-block:: console

    purlcli  --help
    Usage: purlcli [OPTIONS] COMMAND [ARGS]...

      Return information for a PURL or list of PURLs.

    Options:
      --help  Show this message and exit.

    Commands:
      d2d       Run deploy-to-devel "back2source" analysis between packages.
      metadata  Fetch package metadata for a PURL.
      urls      Return known URLs for a PURL.
      validate  Validate PURL syntax and existence.
      versions  List all known versions for a PURL.



The purlcli exposes the following subcommands:

-  validate      Validate PURL syntax.
-  metadata      Fetch package metadata for a PURL.
-  urls          Return known URLs for a PURL.
-  versions      List all known versions for a PURL.
-  d2d           Run deploy-to-devel between packages.


Each subcommand use the same set of options::

    Options:
      --purl PURL    Package-URL or PURL.
      --output FILE  Write output as JSON to FILE. Default is to print on screen.
                     [default: -]
      --file FILE    Read a list of PURLs from a FILE, one per line.
      --help         Show this message and exit.


``validate``: validate a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command validates a PURL in two ways:

* validate that the PURL syntax is correct
* validate that the PURL points to an existing package querying the PurlDB and upstream
  package registries as needed.


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

See also https://public.purldb.io/api/docs/#/validate for details.


----


``versions``: collect package versions for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This command collects and return a list of all the known versions of a PURL by querying the PurlDB
and upstream package registries as needed.


This command collects and return a list of all the known versions of a PURL by querying the PurlDB
and upstream package registries as needed.


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

This command collects and return the metadata for the package pointed by a PURL. It does so by
querying the PurlDB and upstream package registries as needed.

The metadata consist of all available information found in the package manifest and package registry
or repository API.

The schema is the schema used by ScanCode Toolkit, PurlDB and all other AboutCode projects.

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

The intended output for each PURL type supported by the ``metadata`` command is:

- an input PURL with a version: output the metadata for the input version
- an input PURL without a version: output a list of the metadata for all versions


----


``urls``: collect package URLs for a PURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command collects and return the known URL for a PURL. It does so by based on package type/ecosystem
conventions. It optionally also checks if the inferred URLs exists on the web.

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




``d2d``: Run a deployed code to development code analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command runs deploy-to-devel aka. "back2source" analysis between packages.

Its behavior depends on the number of --purl options and their values.

- With a single PURL, run the deploy-to-devel between all the PURLs of the set of PURLs  that
  this PURL belongs to.

- With two PURLs, run the deploy-to-devel between these two PURLs. The first is the "from" PURL,
  and the second is the "to" PURL. The first or "from" PURL is typically the source code or version
  control checkout. The second or "to" PURL is the target of a build or transformnation such as a
  binary, or a source archive.

- You can also provide two HTTP URLs instead of PURLs and  use these as direct download URLs.

This command waits for the run to complete and save results to the `output` FILE.



Examples
########

**Run a d2d analysis between two Java JARs (source and binary)**

You first need to install and run matchcode locally so you have the endpoint accessible. Starting
from a https://github.com/aboutcode-org/purldb/ clone::

    git clone https://github.com/aboutcode-org/purldb
    cd purldb
    make dev
    make envfile
    SECRET_KEY="1" make postgres_matchcodeio
    SECRET_KEY="1" make run_matchcodeio

Then in another shell::

    cd purldb
    source venv/bin/activate

Finally run the command:

.. code-block:: console

    purlcli d2d \
        --purl https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating-sources.jar \
        --purl https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating.jar \
        --matchcode-api-url http://127.0.0.1:8002/api/

*Sample output:*

Here you can see that there are over 730 resources that require review and that may be present in the
binary and not present in the sources.

.. code-block:: json

    {
        "url": "http://127.0.0.1:8002/api/d2d/5d9dbcca-48f0-4788-a356-29196f785c52/",
        "uuid": "5d9dbcca-48f0-4788-a356-29196f785c52",
        "created_date": "2024-06-04T16:31:24.879808Z",
        "input_sources": [
            {
                "uuid": "6b459edd-6b8b-473a-add7-cc79152b4d5e",
                "filename": "htrace-core-4.0.0-incubating-sources.jar",
                "download_url": "https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating-sources.jar#from",
                "is_uploaded": false,
                "tag": "from",
                "size": 42766,
                "is_file": true,
                "exists": true
            },
            {
                "uuid": "bb811a08-ea8c-46b4-8720-865f068ecc0d",
                "filename": "htrace-core-4.0.0-incubating.jar",
                "download_url": "https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating.jar#to",
                "is_uploaded": false,
                "tag": "to",
                "size": 1485031,
                "is_file": true,
                "exists": true
            }
        ],
        "runs": [
            "8689ba05-3859-4eab-b2cf-9bec1495629f"
        ],
        "resource_count": 849,
        "package_count": 1,
        "dependency_count": 0,
        "relation_count": 37,
        "codebase_resources_summary": {
            "ignored-directory": 56,
            "mapped": 37,
            "not-deployed": 1,
            "requires-review": 730,
            "scanned": 25
        },
        "discovered_packages_summary": {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0
        },
        "discovered_dependencies_summary": {
            "total": 0,
            "is_runtime": 0,
            "is_optional": 0,
            "is_pinned": 0
        },
        "codebase_relations_summary": {
            "java_to_class": 34,
            "sha1": 3
        },
        "codebase_resources_discrepancies": {
            "total": 730
        }
    }


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

See https://github.com/aboutcode-org/purldb for support or download.

See https://aboutcode.org for more information about nexB OSS projects.
