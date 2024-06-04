Backup PurlDB database
----------------------

.. code-block:: console

	docker compose exec db pg_dump -U packagedb -Fc packagedb > /path/to/backup.dump


Restore PurlDB database from backup
-----------------------------------

1. Stop all containers and restart ``db``.

.. code-block:: console

    docker compose stop
    docker compose up --detatch db

2. Drop current PurlDB database.

.. code-block:: console

    docker compose exec db dropdb -U packagedb packagedb

3. Recreate PurlDB database.

.. code-block:: console

    TEMPLATE=template0 ENCODING='UTF8' LC_COLLATE='en_US.utf8' LC_CTYPE='en_US.utf8' docker compose exec db createdb --password -U packagedb packagedb

4. Copy PurlDB database backup and restore it.

.. code-block:: console

    docker cp <path to backup.dump> purldb-db-1:/tmp
    docker compose exec db bash
    pg_restore --verbose -U packagedb -d packagedb /tmp/backup.dump


Create a PurlDB API key
-----------------------

.. code-block:: console

    docker compose exec web purldb create-user <user_name>


Create a PurlDB Package scan worker API key
-------------------------------------------

.. code-block:: console

    docker compose exec web purldb create-scan-queue-worker-user <scan_worker_user_name>


