Installation
============

This article will detail the steps needed to set up a PurlDB instance with
MatchCode and package scanning using Docker.

MatchCode.io requires that it is installed and running alongside an instance of
PurlDB, as it needs direct access to PurlDB's data. This is done by running the
PurlDB and MatchCode.io services on the same Docker network.

.. code-block:: console

    docker network create purldb


PurlDB
------

- Clone the PurlDB repo, create an environment file, and build the Docker image

.. code-block:: console

    git clone https://github.com/aboutcode-org/scancode.io.git && cd scancode.io
    make envfile
    docker compose build

Note: if you are running PurlDB on a remote server, be sure to append the
address of your server in this setting in ``docker-compose.yml``

.. code-block:: yaml

    - "traefik.http.routers.web.rule=
        Host(`127.0.0.1`)
        || Host(`localhost`)
        || Host(`your server address`)"

- Create an ``.env`` file:

.. code-block:: console

    make envfile

- Move this ``.env`` file to ``/etc/purldb``:

.. code-block:: console

    sudo mkdir -p /etc/purldb
    sudo cp .env /etc/purldb

- Run your image as a container:

.. code-block:: console

    docker compose up

- You will also need to create a user account for the scan worker:

.. code-block:: console

    docker compose exec web purldb create-scan-queue-worker-user scan_worker_1

Save this API key for use in the ``.env`` file of the Package scan worker

- PurlDB should be running at port 80 on your Docker host. Go to the PurlDB
  address on a web browser to access the web UI.


Package Scan Worker
-------------------

- This should be installed on another machine, if possible.

- Download the latest release of ScanCode.io at
  https://github.com/aboutcode-org/scancode.io/releases and follow the Docker
  installation instructions at
  https://scancodeio.readthedocs.io/en/latest/installation.html

- In the ``.env`` file for ScanCode.io, set the following environment
  variables ``PURLDB_URL`` and ``PURLDB_API_KEY``

.. code-block:: console

    PURLDB_URL=<PurlDB URL>
    PURLDB_API_KEY=<PurlDB API key>

Use the address of your PurlDB server for ``PURLDB_URL`` and the
``PURLDB_API_KEY`` generated from the PurlDB install.

- Move this ``.env`` file to ``/etc/scancodeio``:

.. code-block:: console

    sudo mkdir -p /etc/scancodeio
    sudo cp .env /etc/scancodeio

- To run the worker, you must reference the
  ``docker-compose.purldb-scan-worker.yml`` Compose file:

.. code-block:: console

    docker compose -f docker-compose.purldb-scan-worker.yml up


MatchCode.io
------------

- This should be installed on the same machine as PurlDB.

- Clone the PurlDB repo, create an environment file, and build the Docker
  image using the ``docker-compose.matchcodeio.yml`` Compose file:

.. code-block:: console

    git clone https://github.com/aboutcode-org/scancode.io.git && cd scancode.io
    make envfile
    docker compose -f docker-compose.matchcodeio.yml build

- Move this ``.env`` file to ``/etc/matchcodeio`` and ``/etc/scancodeio``:

.. code-block:: console

    sudo mkdir -p /etc/matchcodeio
    sudo cp .env /etc/matchcodeio
    sudo cp .env /etc/scancodeio

We need to put ``.env`` in the ``/etc/scancodeio`` directory because the
settings of ScanCode.io are loaded before MatchCode.io's settings, as it is
based off of ScanCode.io.

- Run your image as a container:

.. code-block:: console

    docker compose -f docker-compose.matchcodeio.yml up


Local development installation
------------------------------

Supported Platforms
^^^^^^^^^^^^^^^^^^^

**PurlDB** has been tested and is supported on the following operating systems:

    #. **Debian-based** Linux distributions


Pre-installation Checklist
^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you install ScanCode.io, make sure you have the following prerequisites:

 * **Python: versions 3.10 to 3.12** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 11 or later found at https://www.postgresql.org/ or
   https://postgresapp.com/ on macOS

.. _system_dependencies:

System Dependencies
^^^^^^^^^^^^^^^^^^^

In addition to the above pre-installation checklist, there might be some OS-specific
system packages that need to be installed before installing ScanCode.io.

On **Linux**, several **system packages are required** by the ScanCode toolkit.
Make sure those are installed before attempting the ScanCode.io installation::

    sudo apt-get install \
        build-essential python3-dev libssl-dev libpq-dev \
        bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libpopt0 \
        libgpgme11 libdevmapper1.02.1 libguestfs-tools

See also `ScanCode-toolkit Prerequisites <https://scancode-toolkit.readthedocs.io/en/
latest/getting-started/install.html#prerequisites>`_ for more details.


Clone and Configure
^^^^^^^^^^^^^^^^^^^

 * Clone the `PurlDB GitHub repository <https://github.com/aboutcode-org/purldb>`_::

    git clone https://github.com/aboutcode-org/purldb.git && cd purldb

 * Inside the :guilabel:`purldb/` directory, install the required dependencies::

    make dev

 .. note::
    You can specify the Python version during the ``make dev`` step using the following
    command::

        make dev PYTHON_EXE=python3.11

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is
    used.

 * Create an environment file::

    make envfile

Database
^^^^^^^^

**PostgreSQL** is the preferred database backend and should always be used on
production servers.

* Create the PostgreSQL user, database, and table with::

    make postgresdb

.. warning::
    The ``make postgres`` command is assuming that your PostgreSQL database template is
    using the ``en_US.UTF-8`` collation.
    If you encounter database creation errors while running this command, it is
    generally related to an incompatible database template.

    You can either `update your template <https://stackoverflow.com/a/60396581/8254946>`_
    to fit the purldb default, or provide custom values collation using the
    ``POSTGRES_INITDB_ARGS`` variable such as::

        make postgresdb POSTGRES_INITDB_ARGS=\
            --encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8

Tests
^^^^^

You can validate your PurlDB installation by running the tests suite::

    make test

Web Application
^^^^^^^^^^^^^^^

A web application is available to create and manage your projects from a browser;
you can start the local webserver and access the app with::

    make run

Then open your web browser and visit: http://localhost:8000/ to access the web
application.

.. warning::
    This setup is **not suitable for deployments** and **only supported for local
    development**.
    It is highly recommended to use the Docker setup to ensure the
    availability of all the features and the benefits from asynchronous workers
    for pipeline executions.

Upgrading
^^^^^^^^^

If you already have the PurlDB repo cloned, you can upgrade to the latest version
with::

    cd purldb
    git pull
    make dev
    make migrate
