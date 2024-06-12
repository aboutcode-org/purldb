Usage
======


Populate PurlDB
-------------------

Start the PurlDB server by running:
::

    make run

Start the MatchCode.io server by running:
::

    make run_matchcodeio

To start visiting upstream package repositories for package metadata:
::

    make run_visit

To populate the PackageDB using visited package metadata:
::

    make run_map


Populating Package Resource Data
---------------------------------

The Resources of Packages can be collected using the scan queue. By default, a
scan request will be created for each mapped Package.

Given that you have access to a ScanCode.io instance, the following environment
variables will have to be set for the scan queue commands to work:
::

    SCANCODEIO_URL=<ScanCode.io API URL>
    SCANCODEIO_API_KEY=<ScanCode.io API Key>

Package Resource data can also be gathered by running ClearCode, where Package
scan data from clearlydefined is collected and its results are used to create
Packages and Resources.
::

    make clearsync

After some ClearlyDefined harvests and definitions have been obtained, run
``clearindex`` to create Packages and Resources from the harvests and
definitions.
::

    make clearindex

The Package and Package Resource information will be used to create the matching indices.

Once the PackageDB has been populated, run the following command to create the
matching indices from the collected Package data:
::

    make index_packages
