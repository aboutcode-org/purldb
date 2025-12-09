.. _purl_watch:

===============================================
Maintaining an Up-to-Date PurlDB with PurlWatch
===============================================

PurlDB serves as a knowledge base for packages. It is essential to
keep this knowledge base updated as new package versions are released daily.
PurlWatch is responsible for keeping PurlDB up-to-date. Depending on the PurlDB
size, PurlWatch provides two different approaches.

Methods to Keep PurlDB Updated
------------------------------

Using the Management Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a relatively small and focused PurlDB, one can use the management
command ``python manage_purldb.py watch_packages``. This command can be
run periodically using a cron job to watch all the PURLs in your PurlDB for
new versions. Upon detecting new versions, it collects and indexes the new package.
This approach is efficient for smaller databases.

Using the /api/watch Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For larger PurlDB, the ``/api/watch`` endpoint is ideal. Users can use this endpoint
to register interest for a PURL and specify how frequently to check for new versions
of package. Additionally, it includes a depth field to specify the level of data collection,
such as version only, metadata, or a complete scan.

How Watch API Endpoint Works
-----------------------------

The ``/api/watch`` endpoint allows users to register interest in a specific PURL and periodically
monitors it for new version. To effectively manage this periodic monitoring, PurlWatch
uses a comprehensive ``PackageWatch`` model. The ``watch_interval`` field determines how often to
look for new package version. The ``depth`` field specifies the level of data collection, whether
it's just the version, metadata, or a full scan. Errors encountered during the watch process are
tracked in ``watch_error`` and resets after each new watch. The ``schedule_work_id`` keeps track
of the periodic job for a PURL throughout its lifecycle from creation, modification to deletion.
The ``is_active`` field allows users to pause and resume the watch for any PURL, providing
fine-grained control over the entire watch process.

The watch feature utilizes the RQ scheduler to keep track of when a particular PURL is due for
watch. It creates watch task for the PURL and enqueues it in RQ for execution.

Advantages
~~~~~~~~~~
    - Background tasks ensure that the PurlDB remains updated without manual intervention.
    - The watch frequency can be customized to balance the resource usage.
    - Users can define the depth of data collection based on their needs.

.. tip::

   For detailed instructions on using ``/api/watch`` endpoint, refer to :ref:`purl_watch_how_to`.
