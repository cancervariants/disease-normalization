"""Module to test the schemas module."""

import pytest
from ga4gh.core.models import Coding

from disease.schemas import (
    NAMESPACE_TO_SYSTEM_URI,
    NamespacePrefix,
    coding_to_concept_id,
    concept_id_to_coding,
)


def test_namespace_to_system_uri():
    """Ensure that each NamespacePrefix is included in NAMESPACE_TO_SYSTEM_URI"""
    for v in NamespacePrefix.__members__.values():
        assert v in NAMESPACE_TO_SYSTEM_URI, v
        assert NAMESPACE_TO_SYSTEM_URI[v].startswith("http"), v


@pytest.fixture(scope="session")
def concept_id_codings():
    return {
        "mondo:0005072": Coding(
            id="MONDO_0005072",
            system="https://purl.obolibrary.org/obo/",
            code="MONDO:0005072",
        ),
        "DOID:769": Coding(
            id="DOID:769",
            system="https://disease-ontology.org/?id=",
            code="DOID:769",
        ),
        "oncotree:NBL": Coding(
            id="oncotree:NBL",
            system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
            code="NBL",
        ),
        "efo:0000621": Coding(
            id="efo:0000621",
            system="http://www.ebi.ac.uk/efo/EFO_",
            code="0000621",
        ),
        "orphanet:635": Coding(
            id="orphanet:635",
            system="https://www.orpha.net",
            code="635",
        ),
        "medgen:18012": Coding(
            id="medgen:18012",
            system="https://www.ncbi.nlm.nih.gov/medgen/",
            code="18012",
        ),
        "gard:7185": Coding(
            id="gard:7185",
            system="https://rarediseases.info.nih.gov",
            code="7185",
        ),
        "icdo:9500/3": Coding(
            id="icdo:9500/3",
            system="https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
            code="9500/3",
        ),
        "mesh:D009447": Coding(
            id="mesh:D009447",
            system="https://meshb.nlm.nih.gov/record/ui?ui=",
            code="D009447",
        ),
        "umls:C0027819": Coding(
            id="umls:C0027819",
            system="https://www.nlm.nih.gov/research/umls/index.html",
            code="C0027819",
        ),
        "umls:C2751421": Coding(
            id="umls:C2751421",
            system="https://www.nlm.nih.gov/research/umls/index.html",
            code="C2751421",
        ),
    }


def test_coding_to_concept_id(concept_id_codings: dict[str, Coding]):
    for concept_id, coding in concept_id_codings.items():
        assert coding_to_concept_id(coding) == concept_id


def test_concept_id_to_coding(concept_id_codings: dict[str, Coding]):
    for concept_id, coding in concept_id_codings.items():
        assert concept_id_to_coding(concept_id) == coding
        assert concept_id_to_coding(concept_id.lower()) == coding
