"""Test Oncotree ETL methods."""
import pytest
from disease.schemas import MatchType, SourceName
from disease.query import QueryHandler


@pytest.fixture(scope='module')
def oncotree():
    """Build OncoTree ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='oncotree')
            return response['source_matches'][SourceName.ONCOTREE]
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Return neuroblastoma test fixture."""
    return {
        "label": "Neuroblastoma",
        "concept_id": "oncotree:NBL",
        "aliases": [],
        "xrefs": ["ncit:C3270"],
        "associated_with": ["umls:C0027819"],
        "pediatric_disease": None
    }


@pytest.fixture(scope='module')
def nsclc():
    """Return non small cell lung cancer fixture"""
    return {
        "label": "Non-Small Cell Lung Cancer",
        "concept_id": "oncotree:NSCLC",
        "aliases": [],
        "xrefs": ["ncit:C2926"],
        "associated_with": ["umls:C0007131"],
        "pediatric_disease": None
    }


@pytest.fixture(scope='module')
def ipn():
    """Return fixture for intracholecystic papillary neoplasm"""
    return {
        "label": "Intracholecystic Papillary Neoplasm",
        "concept_id": "oncotree:ICPN",
        "aliases": [],
        "xrefs": [],
        "associated_with": [],
        "pediatric_disease": None
    }


def test_concept_id_match(oncotree, neuroblastoma, nsclc, ipn,
                          compare_records):
    """Test that concept ID search resolves to correct record"""
    response = oncotree.search('oncotree:NBL')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('oncotree:NSCLC')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, nsclc)

    response = oncotree.search('oncotree:icpn')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, ipn)

    response = oncotree.search('oncotree:ICPN')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, ipn)

    response = oncotree.search('ipn')
    assert response['match_type'] == MatchType.NO_MATCH


def test_label_match(oncotree, neuroblastoma, nsclc, ipn, compare_records):
    """Test that label search resolves to correct record."""
    response = oncotree.search('Neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('non-small cell lung cancer')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, nsclc)

    response = oncotree.search('intracholecystic papillary neoplasm')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, ipn)


def test_associated_with_match(oncotree, neuroblastoma, nsclc,
                               compare_records):
    """Test that associated_with search resolves to correct record."""
    response = oncotree.search('umls:c0027819')
    assert response['match_type'] == MatchType.ASSOCIATED_WITH
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('umls:C0007131')
    assert response['match_type'] == MatchType.ASSOCIATED_WITH
    assert len(response['records']) == 1
    actual_disease = response['records'][0]
    compare_records(actual_disease, nsclc)


def test_meta(oncotree):
    """Test that meta field is correct."""
    response = oncotree.search('neuroblastoma')
    assert response['source_meta_']['data_license'] == 'CC BY 4.0'
    assert response['source_meta_']['data_license_url'] == \
        'https://creativecommons.org/licenses/by/4.0/legalcode'
    assert response['source_meta_']['version'] == '2020_10_01'
    assert response['source_meta_']['data_url'] == \
        'http://oncotree.mskcc.org/#/home?tab=api'
    assert response['source_meta_']['rdp_url'] is None
    assert response['source_meta_']['data_license_attributes'] == {
        "non_commercial": False,
        "share_alike": False,
        "attribution": True
    }
