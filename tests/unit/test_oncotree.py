"""Test Oncotree ETL methods."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler
from typing import Dict


@pytest.fixture(scope='module')
def oncotree():
    """Build OncoTree ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='oncotree')
            return response['source_matches']['OncoTree']
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Return neuroblastoma test fixture."""
    return {
        "label": "Neuroblastoma",
        "concept_id": "oncotree:NBL",
        "aliases": [],
        "other_identifiers": ["umls:C0027819", "ncit:C3270"],
        "xrefs": [],
        "pediatric_disease": None
    }


@pytest.fixture(scope='module')
def nsclc():
    """Return non small cell lung cancer fixture"""
    return {
        "label": "Non-Small Cell Lung Cancer",
        "concept_id": "oncotree:NSCLC",
        "aliases": [],
        "other_identifiers": ["umls:C0007131", "ncit:C2926"],
        "xrefs": [],
        "pediatric_disease": None
    }


@pytest.fixture(scope='module')
def ipn():
    """Return fixture for intracholecystic papillary neoplasm"""
    return {
        "label": "Intracholecystic Papillary Neoplasm",
        "concept_id": "oncotree:ICPN",
        "aliases": [],
        "other_identifiers": [],
        "xrefs": [],
        "pediatric_disease": None
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
    assert actual_record['pediatric_disease'] is \
        fixture_record['pediatric_disease']


def test_concept_id_match(oncotree, neuroblastoma, nsclc, ipn):
    """Test that concept ID search resolves to correct record"""
    response = oncotree.search('oncotree:NBL')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('oncotree:NSCLC')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, nsclc)

    response = oncotree.search('oncotree:icpn')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, ipn)

    response = oncotree.search('oncotree:ICPN')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, ipn)

    response = oncotree.search('ipn')
    assert response['match_type'] == MatchType.NO_MATCH


def test_label_match(oncotree, neuroblastoma, nsclc, ipn):
    """Test that label search resolves to correct record."""
    response = oncotree.search('Neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = oncotree.search('non-small cell lung cancer')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, nsclc)

    response = oncotree.search('intracholecystic papillary neoplasm')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, ipn)


def test_meta(oncotree):
    """Test that meta field is correct."""
    response = oncotree.search('neuroblastoma')
    assert response['meta_'].data_license == 'CC BY 4.0'
    assert response['meta_'].data_license_url == \
        'https://creativecommons.org/licenses/by/4.0/legalcode'
    assert response['meta_'].version == '2020_10_01'
    assert response['meta_'].data_url == \
        'http://oncotree.mskcc.org/#/home?tab=api'
    assert response['meta_'].rdp_url is None
    assert response['meta_'].data_license_attributes == {
        "non_commercial": False,
        "share_alike": False,
        "attribution": True
    }
