"""Test retrieval of Disease Ontology source data."""

import pytest

from disease.etl.do import DO
from disease.schemas import Disease, MatchType


@pytest.fixture(scope="module")
def do(test_source):
    """Provide test DO query endpoint"""
    return test_source(DO)


@pytest.fixture(scope="module")
def neuroblastoma():
    """Build neuroblastoma fixture."""
    return Disease(
        concept_id="DOID:769",
        label="neuroblastoma",
        xrefs=["ncit:C3270"],
        associated_with=[
            "efo:0000621",
            "gard:7185",
            "icdo:9500/3",
            "mesh:D009447",
            "orphanet:635",
            "umls:C0027819",
        ],
        aliases=[],
    )


@pytest.fixture(scope="module")
def pediatric_liposarcoma():
    """Create test fixture for pediatric liposarcoma."""
    return Disease(
        concept_id="DOID:5695",
        label="childhood liposarcoma",
        xrefs=["ncit:C8091"],
        associated_with=["umls:C0279984"],
        aliases=["pediatric liposarcoma"],
    )


@pytest.fixture(scope="module")
def richter():
    """Create test fixture for Richter's Syndrome."""
    return Disease(
        concept_id="DOID:1703",
        label="Richter's syndrome",
        aliases=["Richter syndrome"],
        xrefs=["ncit:C35424"],
        associated_with=["umls:C0349631", "gard:7578", "icd10.cm:C91.1"],
    )


def test_concept_id_match(
    do, neuroblastoma, pediatric_liposarcoma, richter, compare_response
):
    """Test that concept ID search resolves to correct record"""
    response = do.search("DOID:769")
    compare_response(response, MatchType.CONCEPT_ID, neuroblastoma)

    response = do.search("doid:5695")
    compare_response(response, MatchType.CONCEPT_ID, pediatric_liposarcoma)

    response = do.search("DOid:1703")
    compare_response(response, MatchType.CONCEPT_ID, richter)

    response = do.search("5695")
    assert response.match_type == MatchType.NO_MATCH


def test_label_match(do, neuroblastoma, pediatric_liposarcoma, compare_response):
    """Test that label searches resolve to correct records."""
    response = do.search("childhood liposarcoma")
    compare_response(response, MatchType.LABEL, pediatric_liposarcoma)

    response = do.search("NEUROBLASTOMA")
    compare_response(response, MatchType.LABEL, neuroblastoma)


def test_alias_match(do, richter, compare_response):
    """Test that alias searches resolve to correct records."""
    response = do.search("Richter Syndrome")
    compare_response(response, MatchType.ALIAS, richter)


def test_xref_match(do, neuroblastoma, pediatric_liposarcoma, compare_response):
    """Test that xref search resolves to correct records."""
    response = do.search("ncit:C3270")
    compare_response(response, MatchType.XREF, neuroblastoma)

    response = do.search("NCIT:C8091")
    compare_response(response, MatchType.XREF, pediatric_liposarcoma)


def test_associated_with_match(
    do, neuroblastoma, pediatric_liposarcoma, richter, compare_response
):
    """Test that associated_with search resolves to correct records."""
    response = do.search("umls:c0027819")
    compare_response(response, MatchType.ASSOCIATED_WITH, neuroblastoma)

    response = do.search("umls:C0279984")
    compare_response(response, MatchType.ASSOCIATED_WITH, pediatric_liposarcoma)

    response = do.search("icd10.cm:c91.1")
    compare_response(response, MatchType.ASSOCIATED_WITH, richter)
