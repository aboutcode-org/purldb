.. _rest_api:

REST API
========

To get started with the REST API, visit the **PurlDB API endpoints** at
http://localhost/api/ or http://localhost:8001/api/ if you run on a
local development setup.

.. _rest_api_authentication:

Authentication
--------------

When the authentication setting :ref:`purldb_settings_require_authentication`
is enabled on a PurlDB instance (disabled by default), you will have to include
an authentication token ``API key`` in the Authorization HTTP header of each request.

The key should be prefixed by the string literal "Token" with whitespace
separating the two strings. For example::

    Authorization: Token abcdef123456

.. warning::
    Your API key is like a password and should be treated with the same care.

Example of a cURL-style command line using an API Key for authentication:

.. code-block:: console

    curl -X GET http://localhost/api/packages/ -H "Authorization:Token abcdef123456"

Example of a Python script:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/packages/"
    headers = {
        "Authorization": "Token abcdef123456",
    }
    params = {
        "page": "2",
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.json()

packages
--------

package list
------------

An API endpoint that provides the ability to list and get packages.

``GET /api/packages/``

.. code-block:: json

    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "url": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/",
                "uuid": "0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
                "filename": "elasticsearch-cli-7.17.9.jar",
                "package_sets": [
                    {
                        "uuid": "6d606be2-57c7-429a-a62e-d07833662c38",
                        "packages": [
                            "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/",
                            "https://public.purldb.io/api/packages/055a7bab-38c6-4a1d-bb57-777b72ea4c99/"
                        ]
                    }
                ],
                "package_content": "binary",
                "purl": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9",
                "type": "maven",
                "namespace": "org.elasticsearch",
                "name": "elasticsearch-cli",
                "version": "7.17.9",
                "qualifiers": "",
                "subpath": "",
                "primary_language": "Java",
                "description": "elasticsearch-cli\nElasticsearch subproject :libs:elasticsearch-cli",
                "release_date": "2023-02-01T00:27:00Z",
                "parties": [
                    {
                        "type": "person",
                        "role": "developper",
                        "name": "Elastic",
                        "email": null,
                        "url": "https://www.elastic.co"
                    }
                ],
                "keywords": [],
                "homepage_url": "https://github.com/elastic/elasticsearch.git",
                "download_url": "https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-cli/7.17.9/elasticsearch-cli-7.17.9.jar",
                "bug_tracking_url": null,
                "code_view_url": "https://github.com/elastic/elasticsearch.git",
                "vcs_url": "https://github.com/elastic/elasticsearch.git",
                "repository_homepage_url": null,
                "repository_download_url": null,
                "api_data_url": null,
                "size": null,
                "md5": null,
                "sha1": "9cb255ad91d178f39b2bffc9635c46caeffbd344",
                "sha256": "55e58a1a0b85aa771b85404782740b8cdeb4c37c88f87391e51bbf955c7af808",
                "sha512": "de2a7ca023b60f5d7a8c6c919495942512cfe9561230a1bf006ac160593573d81cbf356a35240dcc338c7c6aec4b79225ef2266eee5eb9b76a256c74b45e834c",
                "copyright": null,
                "holder": null,
                "declared_license_expression": "elastic-license-v2 AND mongodb-sspl-1.0",
                "declared_license_expression_spdx": "Elastic-2.0 AND SSPL-1.0",
                "license_detections": [],
                "other_license_expression": "apache-2.0 AND (mongodb-sspl-1.0 AND elastic-license-v2)",
                "other_license_expression_spdx": "Apache-2.0 AND (SSPL-1.0 AND Elastic-2.0)",
                "other_license_detections": [],
                "extracted_license_statement": "[{'name': 'Elastic License 2.0', 'url': 'https://raw.githubusercontent.com/elastic/elasticsearch/v7.17.9/licenses/ELASTIC-LICENSE-2.0.txt', 'comments': None, 'distribution': 'repo'}, {'name': 'Server Side Public License, v 1', 'url': 'https://www.mongodb.com/licensing/server-side-public-license', 'comments': None, 'distribution': 'repo'}]",
                "notice_text": null,
                "source_packages": [
                    "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?classifier=sources"
                ],
                "extra_data": {},
                "package_uid": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?uuid=0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
                "datasource_id": null,
                "file_references": [],
                "dependencies": [
                    {
                        "purl": "pkg:maven/net.sf.jopt-simple/jopt-simple@5.0.2",
                        "extracted_requirement": "5.0.2",
                        "scope": "compile",
                        "is_runtime": false,
                        "is_optional": true,
                        "is_resolved": true
                    },
                    {
                        "purl": "pkg:maven/org.elasticsearch/elasticsearch-core@7.17.9",
                        "extracted_requirement": "7.17.9",
                        "scope": "compile",
                        "is_runtime": false,
                        "is_optional": true,
                        "is_resolved": true
                    }
                ],
                "resources": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/resources/",
                "history": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/history/"
            }
        ]
    }

The packages list can be filtered by the following fields:

    - ``type``
    - ``namespace``
    - ``name``
    - ``version``
    - ``qualifiers``
    - ``subpath``
    - ``download_url``
    - ``filename``
    - ``sha1``
    - ``sha256``
    - ``md5``
    - ``size``
    - ``release_date``
    - ``package_url``

For example:

.. code-block:: console

    api_url="http://localhost/api/packages/"
    content_type="Content-Type: application/json"
    payload="sha1=9cb255ad91d178f39b2bffc9635c46caeffbd344"

    curl -X GET "$api_url?$payload" -H "$content_type"


package details
---------------

The package details view returns all information available about a package.

``GET /api/projects/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/``

.. code-block:: json

    {
        "url": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/",
        "uuid": "0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
        "filename": "elasticsearch-cli-7.17.9.jar",
        "package_sets": [
            {
                "uuid": "6d606be2-57c7-429a-a62e-d07833662c38",
                "packages": [
                    "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/",
                    "https://public.purldb.io/api/packages/055a7bab-38c6-4a1d-bb57-777b72ea4c99/"
                ]
            }
        ],
        "package_content": "binary",
        "purl": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9",
        "type": "maven",
        "namespace": "org.elasticsearch",
        "name": "elasticsearch-cli",
        "version": "7.17.9",
        "qualifiers": "",
        "subpath": "",
        "primary_language": "Java",
        "description": "elasticsearch-cli\nElasticsearch subproject :libs:elasticsearch-cli",
        "release_date": "2023-02-01T00:27:00Z",
        "parties": [
            {
                "type": "person",
                "role": "developper",
                "name": "Elastic",
                "email": null,
                "url": "https://www.elastic.co"
            }
        ],
        "keywords": [],
        "homepage_url": "https://github.com/elastic/elasticsearch.git",
        "download_url": "https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-cli/7.17.9/elasticsearch-cli-7.17.9.jar",
        "bug_tracking_url": null,
        "code_view_url": "https://github.com/elastic/elasticsearch.git",
        "vcs_url": "https://github.com/elastic/elasticsearch.git",
        "repository_homepage_url": null,
        "repository_download_url": null,
        "api_data_url": null,
        "size": null,
        "md5": null,
        "sha1": "9cb255ad91d178f39b2bffc9635c46caeffbd344",
        "sha256": "55e58a1a0b85aa771b85404782740b8cdeb4c37c88f87391e51bbf955c7af808",
        "sha512": "de2a7ca023b60f5d7a8c6c919495942512cfe9561230a1bf006ac160593573d81cbf356a35240dcc338c7c6aec4b79225ef2266eee5eb9b76a256c74b45e834c",
        "copyright": null,
        "holder": null,
        "declared_license_expression": "elastic-license-v2 AND mongodb-sspl-1.0",
        "declared_license_expression_spdx": "Elastic-2.0 AND SSPL-1.0",
        "license_detections": [],
        "other_license_expression": "apache-2.0 AND (mongodb-sspl-1.0 AND elastic-license-v2)",
        "other_license_expression_spdx": "Apache-2.0 AND (SSPL-1.0 AND Elastic-2.0)",
        "other_license_detections": [],
        "extracted_license_statement": "[{'name': 'Elastic License 2.0', 'url': 'https://raw.githubusercontent.com/elastic/elasticsearch/v7.17.9/licenses/ELASTIC-LICENSE-2.0.txt', 'comments': None, 'distribution': 'repo'}, {'name': 'Server Side Public License, v 1', 'url': 'https://www.mongodb.com/licensing/server-side-public-license', 'comments': None, 'distribution': 'repo'}]",
        "notice_text": null,
        "source_packages": [
            "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?classifier=sources"
        ],
        "extra_data": {},
        "package_uid": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?uuid=0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
        "datasource_id": null,
        "file_references": [],
        "dependencies": [
            {
                "purl": "pkg:maven/net.sf.jopt-simple/jopt-simple@5.0.2",
                "extracted_requirement": "5.0.2",
                "scope": "compile",
                "is_runtime": false,
                "is_optional": true,
                "is_resolved": true
            },
            {
                "purl": "pkg:maven/org.elasticsearch/elasticsearch-core@7.17.9",
                "extracted_requirement": "7.17.9",
                "scope": "compile",
                "is_runtime": false,
                "is_optional": true,
                "is_resolved": true
            }
        ],
        "resources": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/resources/",
        "history": "https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/history/"
    }

packages actions
----------------

Multiple **actions** are available on packages:

History
^^^^^^^

Return the history of actions taken on the ``package``, e.g. field updates.

Using cURL to get package history:

.. code-block:: console

    api_url="https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/history/"
    content_type="Content-Type: application/json"

    curl -X GET "$api_url" -H "$content_type"

.. code-block:: json

    {
        "history": [
            {
                "message": "New Package created from ResourceURI: https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-cli/7.17.9/elasticsearch-cli-7.17.9.jar via map_uri().",
                "timestamp": "2023-04-28-20:55:59"
            }
        ]
    }


Resources
^^^^^^^^^

Return the ``resources`` of the ``package`` as a list of mappings.

Using cURL to get package resources:

.. code-block:: console

    api_url="https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/resources/"
    content_type="Content-Type: application/json"

    curl -X GET "$api_url" -H "$content_type"

.. code-block:: json

    {
        "count": 7556,
        "next": "https://public.purldb.io/api/packages/97627c6e-9acb-43e0-b8df-28bd92f2b7e5/resources/?page=2",
        "previous": null,
        "results": [
            {
                "package": "https://public.purldb.io/api/packages/97627c6e-9acb-43e0-b8df-28bd92f2b7e5/",
                "purl": "pkg:maven/org.elasticsearch/elasticsearch@7.17.9",
                "path": "config",
                "type": "directory",
                "name": "config",
                "extension": "",
                "size": 0,
                "md5": "",
                "sha1": "",
                "sha256": "",
                "sha512": null,
                "git_sha1": null,
                "mime_type": "",
                "file_type": "",
                "programming_language": "",
                "is_binary": false,
                "is_text": false,
                "is_archive": false,
                "is_media": false,
                "is_key_file": false,
                "detected_license_expression": "",
                "detected_license_expression_spdx": "",
                "license_detections": [],
                "license_clues": [],
                "percentage_of_license_text": null,
                "copyrights": [],
                "holders": [],
                "authors": [],
                "package_data": [],
                "emails": [],
                "urls": [],
                "extra_data": {}
            },
            ...
    }


Get enhanced package data
-------------------------

Return a mapping of enhanced Package data for a given Package

This data is formed by supplanting missing data with other data from packages in the same package set.

Using cURL to get enhanced package data:

.. code-block:: console

    api_url="https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/get_enhanced_package_data/"
    content_type="Content-Type: application/json"

    curl -X GET "$api_url" -H "$content_type"

.. code-block:: json

    {
        "type": "maven",
        "namespace": "org.elasticsearch",
        "name": "elasticsearch-cli",
        "version": "7.17.9",
        "qualifiers": "",
        "subpath": "",
        "package_sets": [
            {
                "uuid": "6d606be2-57c7-429a-a62e-d07833662c38",
                "packages": [
                    "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?uuid=0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
                    "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?classifier=sources&uuid=055a7bab-38c6-4a1d-bb57-777b72ea4c99"
                ]
            }
        ],
        "package_content": "binary",
        "primary_language": "Java",
        "description": "elasticsearch-cli\nElasticsearch subproject :libs:elasticsearch-cli",
        "release_date": "2023-02-01T00:27:00Z",
        "parties": [
            {
                "type": "person",
                "role": "developper",
                "name": "Elastic",
                "email": null,
                "url": "https://www.elastic.co"
            }
        ],
        "keywords": [],
        "homepage_url": "https://github.com/elastic/elasticsearch.git",
        "download_url": "https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-cli/7.17.9/elasticsearch-cli-7.17.9.jar",
        "size": null,
        "md5": null,
        "sha1": "9cb255ad91d178f39b2bffc9635c46caeffbd344",
        "sha256": "55e58a1a0b85aa771b85404782740b8cdeb4c37c88f87391e51bbf955c7af808",
        "sha512": "de2a7ca023b60f5d7a8c6c919495942512cfe9561230a1bf006ac160593573d81cbf356a35240dcc338c7c6aec4b79225ef2266eee5eb9b76a256c74b45e834c",
        "bug_tracking_url": null,
        "code_view_url": "https://github.com/elastic/elasticsearch.git",
        "vcs_url": "https://github.com/elastic/elasticsearch.git",
        "copyright": null,
        "holder": null,
        "declared_license_expression": "elastic-license-v2 AND mongodb-sspl-1.0",
        "declared_license_expression_spdx": "Elastic-2.0 AND SSPL-1.0",
        "license_detections": [],
        "other_license_expression": "apache-2.0 AND (mongodb-sspl-1.0 AND elastic-license-v2)",
        "other_license_expression_spdx": "Apache-2.0 AND (SSPL-1.0 AND Elastic-2.0)",
        "other_license_detections": [],
        "extracted_license_statement": "[{'name': 'Elastic License 2.0', 'url': 'https://raw.githubusercontent.com/elastic/elasticsearch/v7.17.9/licenses/ELASTIC-LICENSE-2.0.txt', 'comments': None, 'distribution': 'repo'}, {'name': 'Server Side Public License, v 1', 'url': 'https://www.mongodb.com/licensing/server-side-public-license', 'comments': None, 'distribution': 'repo'}]",
        "notice_text": null,
        "source_packages": [
            "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?classifier=sources"
        ],
        "extra_data": {},
        "dependencies": [
            {
                "purl": "pkg:maven/net.sf.jopt-simple/jopt-simple@5.0.2",
                "extracted_requirement": "5.0.2",
                "scope": "compile",
                "is_runtime": false,
                "is_optional": true,
                "is_resolved": true
            },
            {
                "purl": "pkg:maven/org.elasticsearch/elasticsearch-core@7.17.9",
                "extracted_requirement": "7.17.9",
                "scope": "compile",
                "is_runtime": false,
                "is_optional": true,
                "is_resolved": true
            }
        ],
        "package_uid": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9?uuid=0bbdcf88-ad07-4970-9272-7d5f4c82cc7b",
        "datasource_id": null,
        "purl": "pkg:maven/org.elasticsearch/elasticsearch-cli@7.17.9",
        "repository_homepage_url": null,
        "repository_download_url": null,
        "api_data_url": null,
        "file_references": []
    }

Reindex package
^^^^^^^^^^^^^^^

Reindex this package instance. This will trigger a new scan for this package and
the package data will be updated from the scan data.

Using cURL to reindex a package:

.. code-block:: console

    api_url="https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/reindex_package/"
    content_type="Content-Type: application/json"

    curl -X GET "$api_url" -H "$content_type"

.. code-block:: json

    {
        "status": "pkg:maven/org.elasticsearch/elasticsearch@7.17.9 has been queued for reindexing"
    }


resources
---------

resources list
--------------

Return a list of resources in the PurlDB.

``GET /api/resources/``

.. code-block:: json

    {
        "count": 6031130,
        "next": "https://public.purldb.io/api/resources/?page=2",
        "previous": null,
        "results": [
            {
                "package": "https://public.purldb.io/api/packages/20b7d376-09c7-45ef-a102-75f7f5eef7e2/",
                "purl": "pkg:npm/cac@6.7.14",
                "path": "package/deno/CAC.ts",
                "type": "file",
                "name": "",
                "extension": "",
                "size": 8133,
                "md5": "969474f21d02f9a1dad6a2e85f4bbd25",
                "sha1": "8c7042781582df3d5f39fd2fabf7d2dd365f1669",
                "sha256": null,
                "sha512": null,
                "git_sha1": null,
                "mime_type": "",
                "file_type": "",
                "programming_language": "",
                "is_binary": false,
                "is_text": false,
                "is_archive": false,
                "is_media": false,
                "is_key_file": false,
                "detected_license_expression": "",
                "detected_license_expression_spdx": "",
                "license_detections": [
                    {
                        "matches": [],
                        "identifier": "none-f9065fa7-3897-50e1-6fe0-0d7ba36748f6",
                        "license_expression": "None"
                    }
                ],
                "license_clues": [],
                "percentage_of_license_text": null,
                "copyrights": [],
                "holders": [],
                "authors": [],
                "package_data": [],
                "emails": [],
                "urls": [],
                "extra_data": {}
            },
            ...
    }

The resources list can be filtered by the following fields:

    - ``package_uuid``
    - ``package_url``
    - ``md5``
    - ``sha1``

For example:

.. code-block:: console

    api_url="http://localhost/api/resources/"
    content_type="Content-Type: application/json"
    payload="sha1=8c7042781582df3d5f39fd2fabf7d2dd365f1669"

    curl -X GET "$api_url?$payload" -H "$content_type"


resources actions
-----------------

One action is available on resources:

Filter by checksum
^^^^^^^^^^^^^^^^^^

Take a mapping, where the keys are the names of the checksum algorthm and the values is a list of checksum values and query those values against the packagedb.

Supported checksum fields are:

    - ``md5``
    - ``sha1``

Multiple checksums field scan be passed in one request.

Using cURL to filter for packages using multiple checksums:

.. code-block:: console

    api_url="https://public.purldb.io/api/resources/filter_by_checksums/"
    content_type="Content-Type: application/json"
    data='{
        "sha1": [
            "8c7042781582df3d5f39fd2fabf7d2dd365f1669"
        ],
        "md5": [
            "969474f21d02f9a1dad6a2e85f4bbd25"
        ]
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "package": "https://public.purldb.io/api/packages/20b7d376-09c7-45ef-a102-75f7f5eef7e2/",
                "purl": "pkg:npm/cac@6.7.14",
                "path": "package/deno/CAC.ts",
                "type": "file",
                "name": "",
                "extension": "",
                "size": 8133,
                "md5": "969474f21d02f9a1dad6a2e85f4bbd25",
                "sha1": "8c7042781582df3d5f39fd2fabf7d2dd365f1669",
                "sha256": null,
                "sha512": null,
                "git_sha1": null,
                "mime_type": "",
                "file_type": "",
                "programming_language": "",
                "is_binary": false,
                "is_text": false,
                "is_archive": false,
                "is_media": false,
                "is_key_file": false,
                "detected_license_expression": "",
                "detected_license_expression_spdx": "",
                "license_detections": [
                    {
                        "matches": [],
                        "identifier": "none-f9065fa7-3897-50e1-6fe0-0d7ba36748f6",
                        "license_expression": "None"
                    }
                ],
                "license_clues": [],
                "percentage_of_license_text": null,
                "copyrights": [],
                "holders": [],
                "authors": [],
                "package_data": [],
                "emails": [],
                "urls": [],
                "extra_data": {}
            }
        ]
    }


validate purl
-------------

Take a purl and check whether it's valid PackageURL or not. Optionally set check_existence to true to check whether the package exists in real world.

Note: As of now check_existence only supports ``cargo``, ``composer``, ``deb``, ``gem``, ``golang``, ``hex``, ``maven``, ``npm``, ``nuget`` and ``pypi`` ecosystems.

``GET /api/validate/?purl=pkg:npm/asdf@1.0.2&check_existence=true``

.. code-block:: json

    {
        "valid": true,
        "exists": true,
        "message": "The provided Package URL is valid, and the package exists in the upstream repo.",
        "purl": "pkg:npm/asdf@1.0.2"
    }


collect
-------

Return Package data for the purl passed in the purl query parameter.

If the package does not exist, we will fetch the Package data and return it in
the same request. Optionally, provide the list of addon_pipelines to run on the
package. Find all addon pipelines at
https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html.

``GET /api/collect/?purl=pkg:npm/asdf@1.0.2``

.. code-block:: json

    [
        {
            "url": "https://public.purldb.io/api/packages/4f3a57de-e367-43c6-a7f1-51633d0ecd45/",
            "uuid": "4f3a57de-e367-43c6-a7f1-51633d0ecd45",
            "filename": "asdf-1.0.2.tgz",
            "package_sets": [],
            "package_content": null,
            "purl": "pkg:npm/asdf@1.0.2",
            "type": "npm",
            "namespace": "",
            "name": "asdf",
            "version": "1.0.2",
            "qualifiers": "",
            "subpath": "",
            "primary_language": "JavaScript",
            "description": "tiny static web server that you can launch instantly in any directory (inspired by https://github.com/ddfreyne/adsf/)",
            "release_date": null,
            "parties": [
                {
                    "type": "person",
                    "role": "author",
                    "name": "alsotang",
                    "email": "alsotang@gmail.com",
                    "url": null
                },
                {
                    "type": "person",
                    "role": "maintainer",
                    "name": "alsotang",
                    "email": "alsotang@gmail.com",
                    "url": null
                }
            ],
            "keywords": [
                "static",
                "web",
                "server"
            ],
            "homepage_url": "https://github.com/alsotang/asdf",
            "download_url": "https://registry.npmjs.org/asdf/-/asdf-1.0.2.tgz",
            "bug_tracking_url": "https://github.com/alsotang/asdf/issues",
            "code_view_url": null,
            "vcs_url": "git+https://github.com/alsotang/asdf.git@53aeca5c74c3d8c1fe88c1f98f8e362389fa1d2a",
            "repository_homepage_url": null,
            "repository_download_url": null,
            "api_data_url": null,
            "size": null,
            "md5": null,
            "sha1": "45b7468df1a6f2ec4826257535f97ea89db943e4",
            "sha256": null,
            "sha512": null,
            "copyright": null,
            "holder": null,
            "declared_license_expression": "mit",
            "declared_license_expression_spdx": "MIT",
            "license_detections": [],
            "other_license_expression": null,
            "other_license_expression_spdx": null,
            "other_license_detections": [],
            "extracted_license_statement": "MIT",
            "notice_text": null,
            "source_packages": [],
            "extra_data": {},
            "package_uid": "pkg:npm/asdf@1.0.2?uuid=4f3a57de-e367-43c6-a7f1-51633d0ecd45",
            "datasource_id": null,
            "file_references": [],
            "dependencies": [
                {
                    "purl": "pkg:npm/express",
                    "extracted_requirement": "^4.9.7",
                    "scope": "dependencies",
                    "is_runtime": true,
                    "is_optional": false,
                    "is_resolved": false
                },
                {
                    "purl": "pkg:npm/mocha",
                    "extracted_requirement": "^1.21.5",
                    "scope": "devDependencies",
                    "is_runtime": false,
                    "is_optional": true,
                    "is_resolved": false
                },
                {
                    "purl": "pkg:npm/should",
                    "extracted_requirement": "^4.0.4",
                    "scope": "devDependencies",
                    "is_runtime": false,
                    "is_optional": true,
                    "is_resolved": false
                },
                {
                    "purl": "pkg:npm/supertest",
                    "extracted_requirement": "^0.14.0",
                    "scope": "devDependencies",
                    "is_runtime": false,
                    "is_optional": true,
                    "is_resolved": false
                }
            ],
            "resources": "https://public.purldb.io/api/packages/4f3a57de-e367-43c6-a7f1-51633d0ecd45/resources/",
            "history": "https://public.purldb.io/api/packages/4f3a57de-e367-43c6-a7f1-51633d0ecd45/history/"
        }

scan_queue
----------

This endpoint provides a queue of Packages to be scanned by the package scan worker. A special key for package scan workers or superusers is needed to access this endpoint.

This endpoint is intended for use with a PurlDB package scan worker and is not intended for users to use directly.

scan_queue actions
------------------

get_next_download_url
^^^^^^^^^^^^^^^^^^^^^

Return a mapping containing a ``download_url`` of a package to be scanned with the list of provided ``pipelines`` for the scan request ``scannable_uri_uuid``.

The names of the pipelines that can be run are listed here: https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html

Using cURL to get next download URL:

.. code-block:: console

    api_url="https://public.purldb.io/api/scan_queue/get_next_download_url/"
    content_type="Content-Type: application/json"
    authorization="Authorization:Token abcdef123456"

    curl -X GET "$api_url" -H "$content_type" -H "$authorization"

.. code-block:: json

    {
        "scannable_uri_uuid": "4f3a57de-e367-43c6-a7f1-51633d0ecd45",
        "download_url": "https://registry.npmjs.org/asdf/-/asdf-1.0.2.tgz",
        "pipelines": ["scan_codebase", "fingerprint_codebase"]
    }

Example of a Python script:

.. code-block:: python

    import requests

    api_url = "https://public.purldb.io/api/scan_queue/get_next_download_url/"
    headers = {
        "Authorization": "Token abcdef123456",
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.json()


update_status
^^^^^^^^^^^^^

Update the status of scan request ``scannable_uri_uuid`` with ``scan_status``

If ``scan_status`` is 'failed', then a ``scan_log`` string is expected and
should contain the error messages for that scan.

If ``scan_status`` is 'scanned', then a ``scan_results_file``,
``scan_summary_file``, and ``project_extra_data`` mapping are expected.
``scan_results_file``, ``scan_summary_file``, and ``project_extra_data`` are
then used to update Package data and its Resources.

Using cURL to update status:

.. code-block:: console

    api_url="https://public.purldb.io/api/scan_queue/update_status/"
    content_type="Content-Type: application/json"
    authorization="Authorization:Token abcdef123456"
    data='{
        "scannable_uri_uuid": "4f3a57de-e367-43c6-a7f1-51633d0ecd45",
        "scan_status": "failed",
        "scan_status": "scanned timed out"
    }'

    curl -X POST "$api_url" -H "$content_type" -H "$authorization" -d "$data"

.. code-block:: json

    {
        "status": "updated scannable_uri 4f3a57de-e367-43c6-a7f1-51633d0ecd45 scan_status to failed"
    }



Package Update Set List
-----------------------

Take a list of purls (where each item is a mapping containing PURL and content_type).

If uuid is given then all purls will be added to package set if it exists else a new set would be created and all the purls will be added to that new set.

Note: There is also a slight addition to the logic where a purl already exists in the database and so there are no changes done to the purl entry it is passed as it is.

Using cURL to update status:

.. code-block:: console

    api_url="https://public.purldb.io/api/scan_queue/update_status/"
    content_type="Content-Type: application/json"
    authorization="Authorization:Token abcdef123456"
    data='{
        "purls": [
            {
                "purl": "pkg:npm/less@1.0.32",
                "content_type": "CURATION"
            }
        ],
        "uuid" : "b67ceb49-1538-481f-a572-431062f382gg"
    }'

    curl -X POST "$api_url" -H "$content_type" -H "$authorization" -d "$data"

.. code-block:: json

    [
        {
            "purl": "pkg:npm/less@1.0.32",
            "updated_status":: "Updated"
        }
    ]


Package Set List
----------------

Return a list of package sets and the package data of packages within

``GET /api/projects/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/``

.. code-block:: json

    {
        "count": 8198,
        "next": "https://public.purldb.io/api/package_sets/?page=2",
        "previous": null,
        "results": [
            {
                "uuid": "9d1655c0-16c7-424f-b027-a141cfdbf706",
                "packages": [
                    {
                        "url": "https://public.purldb.io/api/packages/8a433f5e-372c-4fe1-9fc3-1027ecc9678b/",
                        "uuid": "8a433f5e-372c-4fe1-9fc3-1027ecc9678b",
                        "filename": "rfc8528-data-util-8.0.6.jar",
                        "package_sets": [
                            {
                                "uuid": "9d1655c0-16c7-424f-b027-a141cfdbf706",
                                "packages": [
                                    "https://public.purldb.io/api/packages/8a433f5e-372c-4fe1-9fc3-1027ecc9678b/",
                                    "https://public.purldb.io/api/packages/99b26f6e-b823-4c72-8408-9996f17d30f4/"
                                ]
                            }
                        ],
                        "package_content": "binary",
                        "purl": "pkg:maven/org.opendaylight.yangtools/rfc8528-data-util@8.0.6",
                        "type": "maven",
                        "namespace": "org.opendaylight.yangtools",
                        "name": "rfc8528-data-util",
                        "version": "8.0.6",
                        "qualifiers": "",
                        "subpath": "",
                        "primary_language": "Java",
                        "description": "rfc8528-data-util\nRFC8528 data model utilities",
                        "release_date": "2022-05-25T13:36:00Z",
                        "parties": [],
                        "keywords": [],
                        "homepage_url": null,
                        "download_url": "https://repo1.maven.org/maven2/org/opendaylight/yangtools/rfc8528-data-util/8.0.6/rfc8528-data-util-8.0.6.jar",
                        "bug_tracking_url": null,
                        "code_view_url": null,
                        "vcs_url": null,
                        "repository_homepage_url": null,
                        "repository_download_url": null,
                        "api_data_url": null,
                        "size": null,
                        "md5": null,
                        "sha1": "31157249a6286d5478b5d01e8a29f5de9c33fb80",
                        "sha256": "e1d83077ff746ccce4783971d85b5f3efecc2a5504e7ca7801e29d9f131dfdf2",
                        "sha512": "f633bd2fa6cd1d9a36fb296c373fe750dc48f1310b13bc1d020fe8f6ab7dddaf7ff650b11b910504d25a19b205c7237660e170d19fab9b152eabc6d51bd8525a",
                        "copyright": "Copyright (c) PANTHEON.tech, s.r.o. and others",
                        "holder": null,
                        "declared_license_expression": "epl-1.0",
                        "declared_license_expression_spdx": "EPL-1.0",
                        "license_detections": [],
                        "other_license_expression": "((epl-2.0 OR apache-2.0) AND epl-2.0) AND (epl-1.0 AND epl-2.0)",
                        "other_license_expression_spdx": "((EPL-2.0 OR Apache-2.0) AND EPL-2.0) AND (EPL-1.0 AND EPL-2.0)",
                        "other_license_detections": [],
                        "extracted_license_statement": null,
                        "notice_text": null,
                        "source_packages": [
                            "pkg:maven/org.opendaylight.yangtools/rfc8528-data-util@8.0.6?classifier=sources"
                        ],
                        "extra_data": {},
                        "package_uid": "pkg:maven/org.opendaylight.yangtools/rfc8528-data-util@8.0.6?uuid=8a433f5e-372c-4fe1-9fc3-1027ecc9678b",
                        "datasource_id": null,
                        "file_references": [],
                        "dependencies": [
                            {
                                "purl": "pkg:maven/com.google.guava/guava",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/concepts",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-common",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-data-api",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-data-spi",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-model-api",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-model-spi",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/yang-parser-api",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/rfc8528-data-api",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            },
                            {
                                "purl": "pkg:maven/org.opendaylight.yangtools/rfc8528-model-api",
                                "extracted_requirement": null,
                                "scope": "compile",
                                "is_runtime": false,
                                "is_optional": true,
                                "is_resolved": false
                            }
                        ],
                        "resources": "https://public.purldb.io/api/packages/8a433f5e-372c-4fe1-9fc3-1027ecc9678b/resources/",
                        "history": "https://public.purldb.io/api/packages/8a433f5e-372c-4fe1-9fc3-1027ecc9678b/history/"
                    },
                    ...
                ]
            },
            ...
        ]
    }


to_purl
-------

Return a ``golang_purl`` PackageURL from ``go_package``, a standard go import
string or a go.mod string.

``GET /api/to_purl/?go_package=github.com/gorilla/mux%20v1.8.1``

.. code-block:: json

    {
        "golang_purl": "pkg:golang/github.com/gorilla/mux@v1.8.1"
    }


from_purl
---------

Return a ``git_repo`` from a standard PackageURL ``package_url``.

``GET /api/from_purl/?package_url=pkg:github/ckeditor/ckeditor4-react``

.. code-block:: json

    {
        "git_repo": "git+https://github.com/ckeditor/ckeditor4-react.git"
    }


matching
--------

Given a ScanCode.io JSON output ``upload_file``, match directory and resources
of the codebase in ``upload_file`` to Packages indexed in the PurlDB.

This endpoint runs the ``matching`` pipeline at https://github.com/nexB/purldb/blob/main/matchcode_pipeline/pipelines/matching.py

Using cURL to upload a scan for matching:

.. code-block:: console

    api_url="https://public.purldb.io/api/matching/"
    content_type="Content-Type: application/json"

    curl -X POST "$api_url" -H "$content_type" -F "upload_file=@/home/user/scan.json"

.. code-block:: json

    {
        'url': 'http://testserver/api/matching/d7b3a3f3-87de-44d5-852a-e0fb99b10d89/',
        'uuid': 'd7b3a3f3-87de-44d5-852a-e0fb99b10d89',
        'created_date': '2024-06-03T19:02:28.966557Z',
        'input_sources': [
            {
                'filename': 'scan.json',
                'download_url': '',
                'is_uploaded': True,
                'tag': '',
                'exists': True,
                'uuid': '2f67a376-6ff7-4762-9ea5-e998d8164156'
            }
        ],
        'runs': [
            {
                'url': 'http://testserver/api/runs/74c533f7-b31b-451c-8fff-a5a556a410ce/',
                'pipeline_name': 'matching',
                'status': AbstractTaskFieldsModel.Status.NOT_STARTED,
                'description': '',
                'project': 'http://testserver/api/runs/d7b3a3f3-87de-44d5-852a-e0fb99b10d89/',
                'uuid': '74c533f7-b31b-451c-8fff-a5a556a410ce',
                'created_date': '2024-06-03T19:02:28.968804Z',
                'scancodeio_version': '',
                'task_id': None,
                'task_start_date': None,
                'task_end_date': None,
                'task_exitcode': None,
                'task_output': '',
                'log': '',
                'execution_time': None
            }
        ]
    }
