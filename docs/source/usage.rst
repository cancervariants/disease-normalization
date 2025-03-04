Usage
=====

Overview
--------

The Disease Normalizer provides two different search modes:

* **search**: for each :ref:`source <sources>`, find the record or records that best match the given search string. Returns :ref:`disease records <disease-record-object>`.
* **normalize**: find the normalized concept that best matches the given search string. Return a merged record that incorporates data from all associated records from each source. Returns :ref:`a normalized disease object <normalized-disease-object>`. See :ref:`build_normalization` for more information.

REST endpoints
--------------

Once :ref:`HTTP service is activated<starting-service>`, OpenAPI documentation for the REST endpoints is available under the ``/disease`` path (e.g., with default service parameters, at ``http://localhost:8000/disease``), describing endpoint parameters and response objects, and providing some minimal example queries. A live instance is available at `https://normalize.cancervariants.org/disease <https://normalize.cancervariants.org/disease>`_.

The individual endpoints are:

* ``/disease/search``
* ``/disease/normalize``

Internal Python API
-------------------

Each search mode can be accessed directly within Python using the :py:mod:`query API<disease.query>`:

.. code-block:: pycon

    >>> from disease.database import create_db
    >>> from disease.query import QueryHandler
    >>> q = QueryHandler(create_db())
    >>> normalized_response = q.normalize('NSCLC')
    >>> normalized_response
    >>> normalized_response.match_type
    <MatchType.ALIAS: 60>
    >>> normalized_response.disease.name
    'Lung Non-Small Cell Carcinoma'

Critically, the ``QueryHandler`` class must receive a database interface instance as its first argument. The most straightforward way to construct a database instance, as demonstrated above, is with the :py:meth:`create_db() <disease.database.database.create_db>` method. This method tries to build a database connection based on a number of conditions, which are resolved in the following order:

1) if environment variable ``DISEASE_NORM_ENV`` is set to a value, or if the ``aws_instance`` method argument is True, try to create a cloud DynamoDB connection
2) if the ``db_url`` method argument is given a non-None value, try to create a DB connection to that address (if it looks like a PostgreSQL URL, create a PostgreSQL connection, but otherwise try DynamoDB)
3) if the ``DISEASE_NORM_DB_URL`` environment variable is set, try to create a DB connection to that address (if it looks like a PostgreSQL URL, create a PostgreSQL connection, but otherwise try DynamoDB)
4) otherwise, attempt a DynamoDB connection to the default URL, ``http://localhost:8000``

Users hoping for a more explicit connection declaration may instead call a database class directly, e.g.:

.. code-block:: python

    from disease.database.postgresql import PostgresDatabase
    from disease.query import QueryHandler
    pg_db = PostgresDatabase(
        user="postgres",
        password="matthew_cannon2",
        db_name="disease_normalizer"
    )
    q = QueryHandler(pg_db)

See the API documentation for the :py:mod:`database <disease.database.database>`, :py:mod:`DynamoDB <disease.database.dynamodb>`, and :py:mod:`PostgreSQL <disease.database.postgresql>` modules for more details.

Inputs
------

Disease labels and aliases may sometimes be ambiguous or conflicting, particularly when provided as abbreviations for longer terms. As described below, the Disease Normalizer will return the "best available" match where multiple are available, but users are advised to use concept identifiers or current, approved HGNC symbols where available.

Match types
-----------

The **best match** for a search string is determined by which fields in a disease record that it matches against. The Disease Normalizer will first try to match a search string against known concept IDs and disease terms, then aliases, etc. Matches are case-insensitive but must otherwise be exact.

.. autoclass:: disease.schemas.MatchType
    :members:
    :undoc-members:
    :show-inheritance:
    :noindex:

.. note::

    The `FUZZY_MATCH` Match Type is not currently used by the Disease Normalizer.
