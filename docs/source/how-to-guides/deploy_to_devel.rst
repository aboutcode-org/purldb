.. _deploy_to_devel:

=======================================================
Map deployed code back to source code aka. back2source
=======================================================

In this tutorial we excercise the ScanCode.io pipeline used map the deployed binaries back to the
assumed source code of a package, or map source archives to the sources from a version control
system (VCS) checkout.

This feature is exposed as an API endpoint provided by MatchCode.io. The endpoint can be used
directly or through a command line purlcli tool sub-command.

.. note::
    This tutorial assumes that you have a working installation of PurlDB and MatchCode.io
    If you don't, please refer to the `installation <../purldb/overview.html#installation>`_ page.


Why mapping binary back to sources?
-----------------------------------

Sometimes, the released binaries of an open source package do not match its source code. Or the
source code does not match the code in a version control repo.

There are many reasons for this such as a malicious actor, an oversight from the author, some build
tool injecting extra linked code (such as Uberjars, minified npm), or a software supply chain
compromise, etc.

In all cases this is a potential serious issue as such binary cannot be trusted:

- if the additional or different code in the binary is a malware, this is a major issue (of course!)

- if the there is extra code with an undocumented origin and license, this is a possible FOSS
  license compliance issue or a vector for unknown software vulnerabilities (since the extra code is
  not documented and unknown)

The code analysis feature (aka. back2source) provides analysis pipelines to systematically map and
cross- reference the binaries of a FOSS package to its source code and source repository and report
discrepancies.

We call this the "deployment to development"  analysis or "d2d" as this is about mapping deployed
code (aka. binaries) to the development code (aka. the sources). We have already created a basic
Java and JavaScript d2d pipeline prototype to validate the approach and will extend these and create
pipelines for  native ELF binaries.


The going in assumption for a given package version is that the source code and the binaries
built from this source code should match: the binaries are supposed to be built from their
corresponding source code.

Furthermore, the source code archive for a version should match the corresponding tag or commit
checkout of the source code fetched from the VCS repository, such as a git repository.

Yet these assumption are often proven wrong and the potential for many issues:

- The integrity of a package creation or build may be compromised, like with the XZ Utils backdoor
  <https://en.wikipedia.org/wiki/XZ_Utils_backdoor>_ incident where the source archive of the XZ
  Utils packages had been modified to create a malicious SSH backdoor. These cases need to be
  detected ideally before the source code is even built. back2source has been detecting the
  XZ malicious automake build scripts as requring review, and this using code available before the
  XZ backdoor issue was known.

- Extra code may be provisioned and routinely injected or complied in the final binary without
  malice.

  - For instance, an "UberJAR" is created as a larger Java JAR
    <https://en.wikipedia.org/wiki/JAR_(file_format)>_
    as the combination of multiple JARS. The other JARs are fetched at built time and not present in
    source code form and commonly without metadata to help track their origin. This means that using
    package A, means really using unknowningly A, but also B and C. There are license and security
    implications when the license, origin and vulnerability status of B and C goes undetected. Most
    tools do not detect these extra package inclusions.

  - In another instance, the binaries built from a C or C++ source code package may also embed
    headers and other source code from system package dependencies, typically built statically in
    the binary. There are also potential license and security issues when the license, origin and
    vulnerability status of these embedded packages goes undetected.

Therefore, it is important to be able to trust but verify that the binaries map back to their source
code to avoid malware, software supply chain attacks, vulnerabilities and licensing issues.


How does this work?
----------------------

The deployment to development analysis feature is composed of:

- The deploy_to_devel ScanCode.io pipeline with options to support various technologies
- The MatchCode.io "d2d" API endpoint to facilitate the creation of a project with this pipeline and
  its integration in the PurlDB
- The purlci command line "d2d" sub-command to run the d2d for two PURls, two URLs or between all
  the PURLs of a PURL set.

The ScanCode.io pipeline supports these technologies:

- end-to-end Java package binary to source analysis using bytecode and Java source code analysis.
- end-to-end JavaScript and TypeScript package binary to source analysis. Note that this options
  also considers minified and webpacked JS code which is practically as opaque as native compiled
  binaries.

- end-to-end ELF binaries package binary to source analysis. The focus is on on binaries compiled
  from C (C++ will be implemented separately in the future as it requires additional demangling of
  function signatures). This analysis is based extracting DWARF debug symbols compliation unit
  references.

- end-to-end Go binary executable to source analysis o binary to source analysis. Note that Go is
  special, as while its targets binaries are compiled to ELF, Macho-O and Windows PE/COFF formats,
  depending on the operating system target and can also be anlyzed as an ELF for Linux, a Go
  binary also contains extra information to map source and binaries together through a specific
  data structure. This pipeline will be using this data structure (aka. the pclntab).

In addition, and in order to build proper Package sets that include the binaries, source archives
and the VCS sources, this feature is supported by a library designed to to effectively find the
corresponding source Git repositories, tags and commits for a package version and integrate this in
the PurlDB. This is not always a straightforward task because in many cases the information is not
directly available in a package archive or package manifest metadata. When found, the VCS is grouped
with the binary (or binaries) in a "package set" for a given version of a package.


Finally, the d2d analysis is designed to report discrepancies summary. This consist in a data
structure reported in MatchCode.io API calls to summarize the discrepancies found between
the deployed and development code, or between to development source archives.



Tutorial overall setup
-------------------------

Install PurlDB and matchcode.io from a clone of the PurlDB git repository

Then run these commands::

    git clone https://github.com/aboutcode-org/purldb
    cd purldb
    make dev
    make envfile
    SECRET_KEY="1" make postgres_matchcodeio
    SECRET_KEY="1" make run_matchcodeio

In another separate terminal::

    make run


Tutorial for purlcli d2d
-------------------------

The d2d purlci sub-command runs a deployed code to development code analysis on PURLs or URLs.
Its behavior depends on the number of --purl options and their values.

- With a single PURL, run the deploy-to-devel between all the PURLs of the set of PURLs  that
  this PURL belongs to.

- With two PURLs, run the deploy-to-devel between these two PURLs. The first is the "from" PURL,
  and the second is the "to" PURL. The first or "from" PURL is typically the source code or version
  control checkout. The second or "to" PURL is the target of a build or transformnation such as a
  binary, or a source archive.

- You can also provide two HTTP URLs instead of PURLs and  use these as direct download URLs.

This command waits for the run to complete and save results to the output FILE. If the special file
"-" is provided, the results are printed to the screen.


Open a terminal and run::

    cd purldb
    source venv/bin/activate

Then run a d2d subcommand

1. Run the d2d on a single PURL::

    purlcli d2d \
    --purl pkg:github/expressjs/express@4.19.0 \
    --output - \
    --purldb-api-url  http://127.0.0.1:8001/api/ \
    --matchcode-api-url http://127.0.0.1:8002/api/

2. run the d2d for a pair of PURLs::

    purlcli d2d \
    --purl pkg:github/expressjs/express@4.19.0 \
    --purl pkg:npm/express@4.19.0 \
    --output - \
    --purldb-api-url  http://127.0.0.1:8001/api/ \
    --matchcode-api-url http://127.0.0.1:8002/api/

3. run the d2d for a pair of URLs::

    purlcli d2d \
    --purl https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/from-data.zip \
    --purl https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/to-data.zip \
    --output - \
    --purldb-api-url  http://127.0.0.1:8001/api/ \
    --matchcode-api-url http://127.0.0.1:8002/api/


The JSON output with the d2d results will be printed on screen.


4. Run a d2d analysis between two Java JARs (source and binary)::

    purlcli d2d \
    --purl https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating-sources.jar \
    --purl https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating.jar \
    --output - \
    --purldb-api-url  http://127.0.0.1:8001/api/ \
    --matchcode-api-url http://127.0.0.1:8002/api/

In this output, you can see that there are over 730 resources that require review and that may be
present in the binary and not present in the sources.

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


Tutorial for MatchCode.io api/d2d REST API endpoint
----------------------------------------------------

The d2d endpoint accepts two input URLs and run a d2d project for these inputs.

Basic usage in MatchCode.io
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make a request to the local URL for the /api/d2d endpoint and enter Input URLs

For example these two:

- https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/from-data.zip#from

- https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/to-data.zip#to


.. image:: images/d2d-images/da526ca9-6a8c-4883-951e-26e92597ce0d.png

Then click POST button

.. image:: images/d2d-images/7c9b627d-4d74-4ddc-9e51-18b33b0d86b0.png

Click on the "url" link to obtain the d2d results.


Tutorial for ScanCode.io d2d
----------------------------


Java d2d  in ScanCode.io
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Steps for Java binary analysis can be selectively enabled in th2 main d2d pipeline.

To test the feature:

- Create a new project

- Add these two `Download URLs` exactly as below:

  - binary: https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating.jar#to

  - source: https://repo1.maven.org/maven2/org/apache/htrace/htrace-core/4.0.0-incubating/htrace-core-4.0.0-incubating-sources.jar#from

- Select and execute the "map_deploy_to_develop" pipeline, clicking on the Java option

Here is how it looks:

.. image:: images/d2d-images/1fc96ed7-8afc-4ce5-b8c1-ae0b785c1c4b.png

- When the pipeline run is finished, refresh and click on the "relations"

.. image:: images/d2d-images/cb66805c-56dd-4519-81d5-fe3f8ef84f7a.png

- Here you can see the mapping between source and binaries:

.. image:: images/d2d-images/9483bb93-8e7c-4244-9a78-f7ff40eb2874.png

- In the resource page, there are also file-level mappings details:

.. image:: images/d2d-images/1b9cd82f-4c5c-452b-aad7-02cb738f9733.png


Elf d2d in ScanCode.io
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


ELF d2d analysis that can be selectively used with Elf-specific pipeline steps that look like this:

.. image:: images/d2d-images/d338434d-4e31-4bb9-b708-db952a03d634.png

To test the feature:

- Create a new project

- Add these two `Download URLs` exactly as below using these zip examples:

  - source:  https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/from-data.zip#from

  - binary: https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-elfs/to-data.zip#to

- Select and execute the "map_deploy_to_develop" pipeline, and then click on the "Elf" option

Here is how the project looks like after creation:

.. image:: images/d2d-images/8b852b04-5568-468d-87ce-2e556ac2fc5d.png

- When pipeline run is finished, refresh

.. image:: images/d2d-images/67014257-7a7d-403f-8798-75fb8bd23f88.png

- and click on the "relations" , and you can see the mapping between source and binaries:

.. image:: images/d2d-images/c42ff037-4d05-4fd4-ba24-865609df78d7.png

- At the resource page, there are also file-level mappings details:

.. image:: images/d2d-images/f6995025-ab75-40b7-9503-d1f8509e053f.png


Go d2d in ScanCode.io
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Steps for Go "binary" analysis can be selectively used in the d2d pipelines.

The actual Go-specific pipeline steps look like this:

.. image:: images/d2d-images/d338434d-4e31-4bb9-b708-db952a03d634.png

To test the feature:

- Create a new project

- Add these two `Download URLs` exactly as below using these webpacked examples:

  - source:  https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-go/from-data.zip#from

  - binary: https://github.com/aboutcode-org/scancode.io/raw/main/scanpipe/tests/data/d2d-go/to-data.zip#to

- Select and execute the "map_deploy_to_develop" pipeline, clicking on the Go option

Here is how the project creation looks like:

.. image:: images/d2d-images/4d453ddb-3af3-4470-b6ae-d6251c731d99.png

- When pipeline run is finished, refresh

.. image:: images/d2d-images/1d080401-3512-478f-9dfd-99b94fca5f73.png

- and click on the "relations" , and you can see the mapping between source and binaries:

.. image:: images/d2d-images/d28b0b83-3760-49d6-aa98-6f09826a42e6.png

- At the resource page, there are also file-level mappings details:

.. image:: images/d2d-images/38c59bb5-96c5-40ca-b229-95a63dc2c556.png


JavaScript d2d in ScanCode.io
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analysis of JavaScript minified or webpacked "binaries" is a pipeline option.

The actual JavaScript-specific pipeline steps look like this:

.. image:: images/d2d-images/5878c8f3-85bd-4ba4-a350-0da093096480.png


To test the feature:

- Create a new project

- Add these two `Download URLs` exactly as below using these webpacked examples:

  - source: https://github.com/liferay/alloy-editor/archive/refs/tags/v2.14.10.tar.gz#from

  - binary: https://registry.npmjs.org/alloyeditor/-/alloyeditor-2.14.10.tgz#to

- Select and execute the "map_deploy_to_develop" pipeline, clicking on the JavaScript option

Here is how the project creation looks like:

.. image:: images/d2d-images/9d9df257-db0d-4d01-91e4-34643f38fa5a.png

- When the pipeline run is finished, refresh to display the results:

.. image:: images/d2d-images/b7451ce2-883e-45c6-ba49-0f061203d0df.png

- and click on the "relations" , and you can see the mapping between source and binaries:

.. image:: images/d2d-images/43a5ff56-fb36-45c7-82bb-8b5256759eee.png


- Inthe resource page, there are also file-level mappings details:

.. image:: images/d2d-images/4acd087e-0cd1-4361-a8ee-f7af7681c74e.png
