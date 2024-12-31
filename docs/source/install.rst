.. _install:

Installation
============

The Disease Normalizer can be installed from `PyPI <https://pypi.org/project/disease-normalizer/>`_. Users who have access to a PostgreSQL database and don't need to regenerate the Disease Normalizer database can use the :ref:`quick installation instructions <quick-install>`. To use a DynamoDB instance, or to enable local data updates, use the :ref:`full installation instructions <full-install>`.

.. _dependency-groups:

.. note::

    The Disease Normalizer defines five optional dependency groups in total:

    * ``etl`` provides dependencies for regenerating data from sources. It's necessary for users who don't intend to rely on existing database dumps.
    * ``pg`` provides dependencies for connecting to a PostgreSQL database. It's not necessary for users who are using a DynamoDB backend.
    * ``dev`` provides development dependencies, such as static code analysis. It's required for contributing to the Disease Normalizer, but otherwise unnecessary.
    * ``test`` provides dependencies for running tests. As with ``dev``, it's mostly relevant for contributors.
    * ``docs`` provides dependencies for documentation generation. It's only relevant for contributors.

.. note::

   Source data files are stored using the `wags-tails <https://wags-tails.readthedocs.io>`_ library within source-specific subdirectories of a designated WagsTails data directory. By default, this location is ``~/.local/share/wags_tails/``, but it can be configured by passing a Path directly to a data class on initialization, via the ``WAGS_TAILS_DIR`` environment variable, or via `XDG data environment variables <https://specifications.freedesktop.org/basedir-spec/basedir-spec-0.6.html>`_.


.. _quick-install:

Quick Installation
------------------

Requirements
++++++++++++

* A UNIX-like environment (e.g. MacOS, WSL, Ubuntu)
* Python 3.10+
* A recent version of PostgreSQL (ideally at least 11+)

Package installation
++++++++++++++++++++

Install the Disease Normalizer, and the ``pg`` :ref:`dependency group <dependency-groups>`, via PyPI::

    pip install "disease-normalizer[pg]"

Database setup
++++++++++++++

Create a new PostgreSQL database. For example, using the `psql createdb <https://www.postgresql.org/docs/current/app-createdb.html>`_ utility, and assuming that ``postgres`` is a valid user: ::

    createdb -h localhost -p 5432 -U postgres disease_normalizer

Set the environment variable ``DISEASE_NORM_DB_URL`` to a connection description for that database. See the PostgreSQL `connection string documentation <https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING>`_ for more information: ::

   export DISEASE_NORM_DB_URL=postgres://postgres@localhost:5432/disease_normalizer

Load data
+++++++++

Use the ``disease_norm_update_remote`` shell command to load data from the most recent remotely-stored data dump: ::

    disease_norm_update_remote

Start service
+++++++++++++

Finally, start an instance of the Disease Normalizer API on port 5000: ::

    uvicorn disease.main:app --port=5000

Point your browser to http://localhost:5000/disease/. You should see the SwaggerUI page demonstrating available REST endpoints.

The beginning of the response to a GET request to http://localhost:5000/disease/normalize?q=braf should look something like this:

.. code-block::

   {
     "query": "nsclc",
     "match_type": 60,
     "disease": {
       "id": "normalize.disease.ncit:C2926",
       "primaryCode": "ncit:C2926",
       "label": "Lung Non-Small Cell Carcinoma",

       ...
     }
   }

.. _full-install:

Full Installation
-----------------

Requirements
++++++++++++

* A UNIX-like environment (e.g. MacOS, WSL, Ubuntu) with superuser permissions
* Python 3.10+
* A recent version of PostgreSQL (ideally at least 11+), if using PostgreSQL as the database backend
* An available Java runtime (version 8.x or newer), or Docker Desktop, if using DynamoDB as the database backend

Package installation
++++++++++++++++++++

First, install the Disease Normalizer from PyPI: ::

    pip install "disease-normalizer[etl]"

The ``[etl]`` option installs dependencies necessary for using the ``disease.etl`` package, which performs data loading operations.

Users intending to utilize PostgreSQL to store source data should also include the ``pg`` :ref:`dependency group <dependency-groups>`: ::

    pip install "disease-normalizer[etl,pg]"

Database setup
++++++++++++++

The Disease Normalizer requires a separate database process for data storage and retrieval. See the instructions on database setup and population for the available database options:

* :ref:`dynamodb`
* :ref:`postgres`

By default, the Disease Normalizer will attempt to connect to a DynamoDB instance listening at ``http://localhost:8000``.

Load data
+++++++++

For most data sources, the Disease Normalizer can acquire necessary data automatically. However, data from the `Online Mendelian Inheritance in Man (OMIM) <https://www.omim.org/>`_, ``mimTitles.txt``, must be manually acquired. In order to access OMIM data, users must submit a request `here <https://www.omim.org/downloads>`_. Once approved, the relevant OMIM file (``mimTitles.txt``) should be renamed according to the convention ``omim_YYYYMMDD.tsv``, where ``YYYYMMDD`` indicates the date that the file was generated.

To load all other source data, and then generate normalized records, use the following shell command: ::

    disease_norm_update --update_all --update_merged

This will download the latest available versions of all source data files, extract and transform recognized disease concepts, load them into the database, and construct normalized concept groups.
