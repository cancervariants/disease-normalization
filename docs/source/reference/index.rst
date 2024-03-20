.. _api_reference:

API Reference
=============

Core Modules
------------

.. autosummary::
   :nosignatures:
   :toctree: api/
   :template: module_summary.rst

   disease.query
   disease.schemas

Database Modules
----------------

.. autosummary::
   :nosignatures:
   :toctree: api/database
   :template: module_summary.rst

   disease.database.database
   disease.database.dynamodb
   disease.database.postgresql

.. _etl-api:

ETL Modules
-----------

.. autosummary::
   :nosignatures:
   :toctree: api/etl
   :template: module_summary_inh.rst

   disease.etl.base
   disease.etl.do
   disease.etl.mondo
   disease.etl.ncit
   disease.etl.omim
   disease.etl.oncotree
   disease.etl.merge
