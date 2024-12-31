# Disease Normalizer

[![image](https://img.shields.io/pypi/v/disease-normalizer.svg)](https://pypi.python.org/pypi/disease-normalizer)
[![image](https://img.shields.io/pypi/l/disease-normalizer.svg)](https://pypi.python.org/pypi/disease-normalizer)
[![image](https://img.shields.io/pypi/pyversions/disease-normalizer.svg)](https://pypi.python.org/pypi/disease-normalizer)
[![Actions status](https://github.com/cancervariants/disease-normalization/actions/workflows/checks.yaml/badge.svg)](https://github.com/cancervariants/disease-normalization/actions/workflows/checks.yaml)

<!-- description -->
The Disease Normalizer resolves ambiguous references and descriptions of human diseases to consistently-structured, normalized terms. For concepts extracted from [NCIt](https://ncithesaurus.nci.nih.gov/ncitbrowser/), [Mondo Disease Ontology](https://mondo.monarchinitiative.org/), [The Human Disease Ontology](https://disease-ontology.org/), [OMIM](https://www.omim.org/), and [OncoTree](https://oncotree.info/#/home), it designates a [CURIE](https://en.wikipedia.org/wiki/CURIE), and provides additional metadata like aliases and cross-references.
<!-- /description -->

---

**[Documentation](https://disease-normalizer.readthedocs.io/latest/)** · [Installation](https://disease-normalizer.readthedocs.io/latest/install.html) · [API reference](https://disease-normalizer.readthedocs.io/latest/reference/index.html)

---

## Installation

The Disease Normalizer is available via PyPI:

```commandline

python3 -m pip install disease-normalizer
```

See [installation instructions](https://disease-normalizer.readthedocs.io/latest/install.html) in the documentation for a description of installation options and data setup requirements.

---

## Examples

Use the [live service](https://normalize.cancervariants.org/disease/) to programmatically normalize disease terms, as in the following truncated example:

```shell
$ curl -s 'https://normalize.cancervariants.org/disease/normalize?q=liver%20cancer' | python -m json.tool
{
    "query": "liver cancer",
    "warnings": null,
    "match_type": 80,
    "disease": {
        "conceptType": "Disease",
        "primaryCode": "ncit:C34803",
        "id": "normalize.disease:liver%20cancer",
        "label": "Primary Malignant Liver Neoplasm",
        # ...
    }
}
```

Or utilize the [Python API](https://disease-normalizer.readthedocs.io/latest/reference/api/disease.query.html) for fast local access:

```pycon
>>> from disease.query import QueryHandler
>>> from disease.database import create_db
>>> q = QueryHandler(create_db())
>>> result = q.normalize("NSCLC")
>>> result.disease.primaryCode.root
'ncit:C2926'
```

---

## Feedback and contributing

We welcome bug reports, feature requests, and code contributions from users and interested collaborators. The [documentation](https://disease-normalizer.readthedocs.io/latest/contributing.html) contains guidance for submitting feedback and contributing new code.
