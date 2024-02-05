.. _loading_and_updating_data:

Loading and updating data
=========================

.. note::

    See the :ref:`ETL API documentation<etl-api>` for information on programmatic access to the data loader classes.

Full load/reload
----------------

Calling the Disease Normalizer update command with the ``--update_all`` and ``--update_merged`` flags will delete all existing data, fetch new source data if available, and then perform a complete reload of the database (including merged records):

.. code-block:: shell

    disease_norm_update --update_all --update_merged


Reload individual source
------------------------

To update specific sources, call the ``--sources`` option with one or more source name(s) quoted and separated by spaces. While it is possible to update individual source data without also updating the normalized record data, that may affect the proper function of the normalized query endpoints, so it is recommended to include the ``--update_merged`` flag as well.

.. code-block:: shell

    disease_norm_update --sources="HGNC NCBI" --update_merged


Use local data
--------------

The Disease Normalizer will fetch the latest available data from all sources if local data is out-of-date. To suppress this and force usage of local files, use the `--use_existing` flag:

.. code-block:: shell

    disease_norm_update --update_all --use_existing


Check DB health
---------------

The shell command ``disease_norm_check_db`` performs a basic check on the database status. It first confirms that the database's schema exists, and then identifies whether metadata is available for each source, and whether disease record and normalized concept tables are non-empty. Check the process's exit code for the result (per the UNIX standard, ``0`` means success, and any other return code means failure).

.. code-block:: console

    $ disease_norm_check_db
    $ echo $?
    1  # indicates failure

This command is equivalent to the combination of the database classes' ``check_schema_initialized`` and ``check_tables_populated`` methods:

.. code-block:: python

   from disease.database import create_db
   db = create_db()
   db_is_healthy = db.check_schema_initialized() and db.check_tables_populated()
