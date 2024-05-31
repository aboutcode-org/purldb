.. _rest_api:

REST API
========

To get started with the REST API, visit the **projects' API endpoint** at
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

The project details view returns all information available about a project.

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

Using cURL to get reindex a package:

.. code-block:: console

    api_url="https://public.purldb.io/api/packages/0bbdcf88-ad07-4970-9272-7d5f4c82cc7b/reindex_package/"
    content_type="Content-Type: application/json"

    curl -X GET "$api_url" -H "$content_type"

.. code-block:: json

    {
        "status": "pkg:maven/org.elasticsearch/elasticsearch@7.17.9 has been queued for reindexing"
    }
