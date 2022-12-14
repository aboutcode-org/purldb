===============================
ClearCode toolkit
===============================

ClearCode is a simple tool to fetch and sync ClearlyDefined data for a local copy.

ClearlyDefined data are organized as deeply nested trees of JSON files.

The data that are synchronized include with this tool include:

 - the "definitions" that contain the aggregated data from running multiple scan
   tools and if available a manual expert curation
 - the "harvests" that contain the actual detailed output of scans (e.g. scancode runs)

The items are not fetched for now:

 - the "attachments" that are whole original files such as a README file
 - the "deadletters" that are scan failure traces when things fail: these are
   not available through the API


Here are some stats on the ClearlyDefined data files set as of 2020-02-26,
excluding "deadletters" and most attachments:

+----------------+-------------+-------------+--------------+-----------------+---------+
|                |  JSON Files | Directories | Files & Dirs |    Gzipped Size | On disk |
+================+=============+=============+==============+=================+=========+
| ScanCode scans |   9,087,479 |  29,052,667 |   38,140,146 | 139,754,303,291 | ~400 GB |
+----------------+-------------+-------------+--------------+-----------------+---------+
|  Defs. & misc. |  38,796,760 |  44,825,854 |   83,622,614 | 304,861,913,800 |   ~1 TB |
+----------------+-------------+-------------+--------------+-----------------+---------+
|          Total |  47,884,239 |  73,878,521 |  121,762,760 | 444,616,217,091 |   ~2 TB |
+----------------+-------------+-------------+--------------+-----------------+---------+

Such a large number of files breaks about any filesystem: a mere directory
listing can take days to complete. To avoid these file size and number issues,
the JSON data fetched from the ClearlyDefined API are stored as gzipped-compressed
JSON as blobs in a PosgresSQL database keyed by the file path.
That path is the same as the path used in the ClearlyDefined "blob" storage on Azure.
You can also save these as real files gzipped-compressed JSON files (with the caveat
that this will make the filesystem crumble and this may require a special mkfs
invocation to create a filesystems with enough inodes.)


Requirements
------------

To run this tool, you need:

- a POSIX OS (Linux)
- Python 3.6+
- PosgresSQL 9.5+ if you want to handle a large dataset
- plenty of space, bandwidth and CPU.


Quick start using a simple file storage
---------------------------------------

Run these commands to get started::

    $ source configure
    $ clearsync --help

For instance, try this command::

    $ clearsync --output-dir clearly-local --verbose -n3

This will fetch continuously everything (definitions, harvests, etc). from 
ClearlyDefined using three processes in parallel and save the output as JSON
files in the clearly-local directory.

You can abort this at anytime with Ctrl+C.


WARNING: this may ceate too many files and directory for your file system sanity.
Consider using the PostgreSQL storage instead.
 

Quick start using a database storage
------------------------------------

First create a PostgreSQL database.
This requires sudo access. This is tested on Debian and Ubuntu.
::

    $ ./createdb.sh


Then run these commands to get started::

    $ source configure
    $ clearsync --help


For instance, try this command::

    $ clearsync --save-to-db  --verbose -n3

This will fetch all the latest data items and save them in the "clearcode" 
PostgresDB using three processes in parallel for fetching.
You can abort this at anytime with Ctrl+C.


Basic tests can be run with the following command::

    $ ./manage.py test clearcode --verbosity=2



Using the Rest API and webserver to import and export items from ClearCode
--------------------------------------------------------------------------

This assumes you have already populated your database even partially.
In a first shell, start the webserver::

    $ source configure
    $ ./manage.py runserver

You can then visit the API at http://127.0.0.1:8000/api/

In a second shell, you can run the command line API client tool to export data
fetched from ClearlyDefined::

    $ source configure
    $ python etc/scripts/clearcode-api-backup.py \
      --api-root-url http://127.0.0.1:8000/api/ \
      --last-modified-date 2020-06-20

    Starting backup from http://127.0.0.1:8000/api/
    Collecting cditems...
    821 total
    [...........................................................................]
    821 cditems collected.
    Backup location: /etc/scripts/clearcode_backup_2020-06-23_00-30-22
    Backup completed.

The exported backup is saved as a single JSON file in a directory created for
this run named with a timestamp such as clearcode_backup_2020-06-22_21-04-48.


In that second shell, you can then run the command line API client tool to
import data saved from the export/backup run above::

    $ python etc/scripts/clearcode-api-import.py \
      --clearcode-target-api-url http://127.0.0.1:8000/api/ \
      --backup-directory etc/scripts/clearcode_backup_2020-06-23_00-30-22/

    Importing objects from ../etc/scripts/clearcode_backup_2020-06-23_00-30-22 to http://127.0.0.1:8000/api/
    Copying 821 cditems...........................................Copy completed.
    Results saved in /etc/scripts/copy_results_2020-06-23_00-32-37.json

This would likely something you would run on an isolated ClearCode DB that
you want to keep current with items exported from a live replicating DB.

Note that these tools have minimal external requirements: only the requests
library and have been designed to be used as single files that can be copied
around.

See also for help on these two utilities::

    $ python etc/scripts/clearcode-api-backup.py -h
    $ python etc/scripts/clearcode-api-import.py -h


Support
-------

Enter a ticket with bugs, issues or questions at
https://github.com/nexB/clearcode-toolkit/

And join us to chat on Gitter (also by IRC) at
https://gitter.im/aboutcode-org/discuss


Release TODO
------------

- Merge in master and tag release.
- pip install wheel twine
- rm dist/*
- python setup.py release
- twine upload dist/*


License
-------

Apache-2.0

