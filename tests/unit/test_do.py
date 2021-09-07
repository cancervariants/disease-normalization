"""Test retrieval of Disease Ontology source data."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler


@pytest.fixture(scope='module')
def do():
    """Build NCIt ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='do')
            return response['source_matches']['DO']
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Build neuroblastoma fixture."""
    return {
        "concept_id": "DOID:769",
        "label": "neuroblastoma",
        "xrefs": [
            "ncit:C3270"
        ],
        "associated_with": [
            "efo:0000621",
            "gard:7185",
            "icdo:M9500/3",
            "mesh:D009447",
            "orphanet:635",
            "umls:C0027819",
        ],
        "aliases": []
    }


@pytest.fixture(scope='module')
def pediatric_liposarcoma():
    """Create test fixture for pediatric liposarcoma."""
    return {
        "concept_id": "DOID:5695",
        "label": "childhood liposarcoma",
        "xrefs": ["ncit:C8091"],
        "associated_with": ["umls:C0279984"],
        "aliases": ["pediatric liposarcoma"]
    }


@pytest.fixture(scope='module')
def richter():
    """Create test fixture for Richter's Syndrome."""
    return {
        "concept_id": "DOID:1703",
        "label": "Richter's syndrome",
        "aliases": ["Richter syndrome"],
        "xrefs": ["ncit:C35424"],
        "associated_with": ["umls:C0349631", "gard:7578", "icd10.cm:C91.1"]
    }


def test_concept_id_match(do, neuroblastoma, pediatric_liposarcoma, richter,
                          compare_records):
    """Test that concept ID search resolves to correct record"""
    response = do.search('DOID:769')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = do.search('doid:5695')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = do.search('DOid:1703')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter)

    response = do.search('5695')
    assert response['match_type'] == MatchType.NO_MATCH


def test_label_match(do, neuroblastoma, pediatric_liposarcoma,
                     compare_records):
    """Test that label searches resolve to correct records."""
    response = do.search('pediatric liposarcoma')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = do.search('childhood liposarcoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = do.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)


def test_alias_match(do, richter, compare_records):
    """Test that alias searches resolve to correct records."""
    response = do.search('Richter Syndrome')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter)


def test_xref_match(do, neuroblastoma, pediatric_liposarcoma,
                    compare_records):
    """Test that xref search resolves to correct records."""
    response = do.search('ncit:C3270')
    assert response['match_type'] == MatchType.XREF
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = do.search('NCIT:C8091')
    assert response['match_type'] == MatchType.XREF
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)


def test_associated_with_match(do, neuroblastoma, pediatric_liposarcoma,
                               richter, compare_records):
    """Test that associated_with search resolves to correct records."""
    response = do.search('umls:c0027819')
    assert response['match_type'] == MatchType.ASSOCIATED_WITH
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = do.search('umls:C0279984')
    assert response['match_type'] == MatchType.ASSOCIATED_WITH
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = do.search('icd10.cm:c91.1')
    assert response['match_type'] == MatchType.ASSOCIATED_WITH
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter)
