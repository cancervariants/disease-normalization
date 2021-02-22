"""Test retrieval of Disease Ontology source data."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler
from typing import Dict


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
        "other_identifiers": [
            "ncit:C3270"
        ],
        "xrefs": [
            "efo:0000621",
            "gard:7185",
            "icd.o:M9500/3",
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
        "label": "pediatric liposarcoma",
        "other_identifiers": ["ncit:C8091"],
        "xrefs": ["umls:C0279984"],
        "aliases": []
    }


@pytest.fixture(scope='module')
def richter():
    """Create test fixture for Richter's Syndrome."""
    return {
        "concept_id": "DOID:1703",
        "label": "Richter's syndrome",
        "aliases": ["Richter syndrome"],
        "other_identifiers": ["ncit:C35424"],
        "xrefs": ["umls:C0349631", "gard:7578", "icd10.cm:C91.1"]
    }


def compare_records(actual_record: Dict, fixture_record: Dict):
    """Check that identity records are identical."""
    assert actual_record['concept_id'] == fixture_record['concept_id']
    assert ('label' in actual_record) == ('label' in fixture_record)
    if 'label' in actual_record or 'label' in fixture_record:
        assert actual_record['label'] == fixture_record['label']
    assert ('aliases' in actual_record) == ('aliases' in fixture_record)
    if 'aliases' in actual_record or 'aliases' in fixture_record:
        assert set(actual_record['aliases']) == set(fixture_record['aliases'])
    assert ('other_identifiers' in actual_record) == ('other_identifiers' in fixture_record)  # noqa: E501
    if 'other_identifiers' in actual_record or 'other_identifiers' in fixture_record:  # noqa: E501
        assert set(actual_record['other_identifiers']) == set(fixture_record['other_identifiers'])  # noqa: E501
    assert ('xrefs' in actual_record) == ('xrefs' in fixture_record)
    if 'xrefs' in actual_record or 'xrefs' in fixture_record:
        assert set(actual_record['xrefs']) == set(fixture_record['xrefs'])


def test_concept_id_match(do, neuroblastoma, pediatric_liposarcoma, richter):
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


def test_label_match(do, neuroblastoma, pediatric_liposarcoma):
    """Test that label searches resolve to correct records."""
    response = do.search('pediatric liposarcoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = do.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)


def test_alias_match(do, richter):
    """Test that alias searches resolve to correct records."""
    response = do.search('Richter Syndrome')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter)
