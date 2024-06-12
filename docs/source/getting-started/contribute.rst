Contribute
==========

Documentation to support code and documentation contributions
to purldb.

PURLdb tests
-------------

Run all PURLdb tests
~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    make test


purldb-toolkit
--------------

Run all purldb-toolkit non-live tests (i.e., no live network calls)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    DJANGO_SETTINGS_MODULE=purldb_project.settings pytest -vvs purldb-toolkit/tests/test_purlcli.py


Run all purldb-toolkit live tests (i.e., check actual API endpoints etc.)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    DJANGO_SETTINGS_MODULE=purldb_project.settings pytest -vvs purldb-toolkit/tests/test_purlcli_live.py --run_live_fetch
