Disease Normalizer |version|
============================

.. image:: https://img.shields.io/pypi/v/disease-normalizer.svg
   :alt: PyPI version
   :target: https://pypi.python.org/pypi/disease-normalizer

.. image:: https://img.shields.io/pypi/l/disease-normalizer.svg
   :alt: License
   :target: https://github.com/cancervariants/disease-normalization/blob/main/LICENSE

.. image:: https://img.shields.io/pypi/pyversions/disease-normalizer?color=gr
   :alt: PyPI - supported Python versions

.. image:: https://github.com/cancervariants/disease-normalization/actions/workflows/checks.yaml/badge.svg
   :alt: tests status
   :target: https://github.com/cancervariants/disease-normalization/actions/workflows/checks.yaml

The Disease Normalizer resolves ambiguous references and descriptions of human diseases to consistently-structured, normalized terms. For concepts extracted from `NCIt <https://ncithesaurus.nci.nih.gov/ncitbrowser/>`_, `Mondo Disease Ontology <https://mondo.monarchinitiative.org/>`_, `The Human Disease Ontology <https://disease-ontology.org/>`_, `OMIM <https://www.omim.org/>`_, and `OncoTree <https://oncotree.info/#/home>`_, it designates a `CURIE <https://en.wikipedia.org/wiki/CURIE>`_, and provides additional metadata like aliases and cross-references.

A `public REST instance of the service <https://normalize.cancervariants.org/disease>`_ is available for programmatic queries:

.. code-block:: pycon

   >>> import requests
   >>> result = requests.get("https://normalize.cancervariants.org/disease/normalize?q=nsclc").json()
   >>> result["disease"]["primaryCode"]
   'ncit:C2926'
   >>> next(ext for ext in result["disease"]["extensions"] if ext["name"] == "aliases")["value"][:5]
   ['Non-Small Cell Carcinoma of Lung', 'NSCLC - non-small cell lung cancer', 'Non-small cell lung cancer', 'Non-Small Cell Carcinoma of the Lung', 'non-small cell cancer of the lung']

The Disease Normalizer can also be installed locally as a Python package for fast access:

.. code-block:: pycon

    >>> from disease.query import QueryHandler
    >>> from disease.database import create_db
    >>> q = QueryHandler(create_db())
    >>> result = q.normalize("nsclc")
    >>> result.disease.primaryCode.root
    'ncit:C2926'
    >>> next(ext for ext in result.disease.extensions if ext.name == "aliases").value[:5]
    ['Non-Small Cell Carcinoma of Lung', 'NSCLC - non-small cell lung cancer', 'Non-small cell lung cancer', 'Non-Small Cell Carcinoma of the Lung', 'non-small cell cancer of the lung']

The Disease Normalizer was created to support the `Knowledgebase Integration Project <https://cancervariants.org/projects/integration/>`_ of the `Variant Interpretation for Cancer Consortium (VICC) <https://cancervariants.org/>`_. It is developed primarily by the `Wagner Lab <https://www.nationwidechildrens.org/specialties/institute-for-genomic-medicine/research-labs/wagner-lab>`_. Full source code is available on `GitHub <https://github.com/cancervariants/disease-normalization>`_.

.. toctree::
   :hidden:
   :maxdepth: 2

    Installation<install>
    Managing data<managing_data/index>
    API<reference/index>
    Changelog<changelog>
    Contributing<contributing>
    License<license>
