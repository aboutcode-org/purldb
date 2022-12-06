=========
MatchCode
=========
MatchCode is a server that detects Packages from ScanCode scans of a codebase.

Installation
------------
Requirements
############
* Debian-based Linux distribution
* Python 3.9 or later
* Postgres 13
* git
* scancode-toolkit runtime dependencies (https://scancode-toolkit.readthedocs.io/en/stable/getting-started/install.html#install-prerequisites)

Once the prerequisites have been installed, set up MatchCode with the following commands:
::

    git clone https://github.com/nexb/purldb
    cd purldb/matchcode
    ./configure --dev
    make postgres
    make envfile

Once MatchCode and the database has been set up, run tests to ensure functionality:
::

    make test


Post-Installation
-----------------
If you have an empty PackageDB without Package and Package Resource information, ClearCode Toolkit should be run for a while so it can populate the PackageDB with Package and Package Resource information from clearlydefined.
::
    make clearsync

After some ClearlyDefined harvests and definitions have been obtained, run ``clearindex`` to create Packages and Resources from the harvests and definitions.
::
    make clearindex

The Package and Package Resource information will be used to create the matching indices.
Once the PackageDB has been populated, run the following command to create the matching indices from the collected Package data:
::
    make index_packages


Usage
-----
Start the MatchCode server by running:
::
    make run

You can send a ScanCode JSON scan for matching at the api/match_request/ endpoint using the HTML view or API.

There are currently four types of matching that MatchCode provides:

* Exact Package archive matching

  * Check the SHA1 values of archives from a scan to determine if they are known Packages

* Exact Package file matching

  * Check the SHA1 values of files from a scan to see what Packages also has that file

* Approximate Directory structure matching

  * Check to see if a directory and the files under it is from a known Package using the name of the files

* Approximate Directory content matching

  * Check to see if a directory and the files under it is from a known Package using the SHA1 values of the files
