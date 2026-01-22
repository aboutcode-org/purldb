Installation
=============

Instruction for a standalone purldb installation.

Requirements
-------------

* Debian-based Linux distribution
* Python 3.11 or later
* Postgres 13
* git
* scancode-toolkit runtime dependencies (https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)
* ``libpq-dev``
*     If you are using Debian or Ubuntu : ``sudo apt install libpq-dev``
*     If you are using Fedora: ``sudo dnf install libpq-devel``

Installation steps
-------------------

Once the prerequisites have been installed, set up PurlDB with the following commands:
::

    git clone https://github.com/nexb/purldb
    cd purldb
    make dev
    make envfile
    make postgres
    make postgres_matchcodeio

Indexing some PURLs requires a GitHub API token. Please add your GitHub API key to the `.env` file
::

    GH_TOKEN=your-github-api


Once PurlDB and the database has been set up, run tests to ensure functionality:
::

    make test
