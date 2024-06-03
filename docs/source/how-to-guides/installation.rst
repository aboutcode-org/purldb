Installation
============

This article will detail the steps needed to set up a PurlDB instance with
MatchCode and package scanning using Docker.


You will first need to create a Docker network for PurlDB. This is necessary for
MatchCode.io to acess PurlDB's database.::

    docker network create purldb


PurlDB
------

  - Clone the PurlDB repo, create an environment file, and build the Docker image::

        git clone https://github.com/nexB/scancode.io.git && cd scancode.io
        make envfile
        docker compose build

    Note: if you are running PurlDB on a remote server, be sure to update
    ``127.0.0.1`` and ``localhost`` to the address of your server in
    ``docker-compose.yml`` ::

        - "traefik.http.routers.web.rule=
          Host(`127.0.0.1`)
          || Host(`localhost`)"

  - Create an ``.env`` file::

        make envfile

  - Move this ``.env`` file to ``/etc/purldb``:::

        sudo mkdir -p /etc/purldb
        sudo cp .env /etc/purldb

  - Run your image as a container::

        docker compose up

  - You will also need to create a user account for the scan worker::

        docker compose exec web purldb create-scan-queue-worker-user scan_worker_1

    Save this API key for use in the ``.env`` file of the Package scan worker

  - At this point, PurlDB should be running at port 80 on your Docker host. Go
    to the PurlDB address on a web browser to access the web UI.


Package Scan Worker
-------------------

  - This should be installed on another machine, if possible.

  - Download the latest release of ScanCode.io at
    https://github.com/nexB/scancode.io/releases and follow the Docker
    installation instructions at
    https://scancodeio.readthedocs.io/en/latest/installation.html

  - In the ``.env`` file for ScanCode.io, set the following environment
    variables::

        PURLDB_URL = env.str("PURLDB_URL", default="")
        PURLDB_API_KEY = env.str("PURLDB_API_KEY", default="")

    Use the address of your PurlDB server for ``PURLDB_URL`` and the
    ``PURLDB_API_KEY`` generated from the PurlDB install.

  - Move this ``.env`` file to ``/etc/scancodeio``:::

        sudo mkdir -p /etc/scancodeio
        sudo cp .env /etc/scancodeio

  - To run the worker, you must reference the
    ``docker-compose.purldb-scan-worker.yml`` Compose file::

        docker compose -f docker-compose.purldb-scan-worker.yml up


MatchCode.io
------------

  - This should be installed on the same machine as PurlDB.

  - Clone the PurlDB repo, create an environment file, and build the Docker
    image using the ``docker-compose.matchcodeio.yml`` Compose file::

        git clone https://github.com/nexB/scancode.io.git && cd scancode.io
        make envfile
        docker compose -f docker-compose.matchcodeio.yml build

  - Move this ``.env`` file to ``/etc/matchcodeio`` and ``/etc/scancodeio``:::

        sudo mkdir -p /etc/matchcodeio
        sudo cp .env /etc/matchcodeio
        sudo cp .env /etc/scancodeio

    We need to put ``.env`` in the ``/etc/scancodeio`` directory because the
    settings of ScanCode.io are loaded before MatchCode.io's settings, as it is
    based off of ScanCode.io.

  - Run your image as a container::

        docker compose -f docker-compose.matchcodeio.yml up

