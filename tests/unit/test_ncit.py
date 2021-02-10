"""Test NCIt source."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler
from typing import Dict


@pytest.fixture(scope='module')
def ncit():
    """Build NCIt ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='ncit')
            return response['source_matches']['NCIt']
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Build neuroblastoma test fixture."""
    return {
        "label_and_type": "ncit:c3270##identity",
        "concept_id": "ncit:C3270",
        "label": "Neuroblastoma",
        "aliases": [
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (NBL)",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma, NOS",
            "neuroblastoma"
        ],
        "other_identifiers": [],
        "xrefs": ["umls:C0027819"],
        "src_name": "NCIt"
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


def test_concept_id_match(ncit, neuroblastoma):
    """Test that concept ID search resolves to correct record"""
    response = ncit.search('ncit:C3270')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('ncit:c3270')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('NCIT:C3270')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('C3270')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('3270')
    assert response['match_type'] == MatchType.NO_MATCH


def test_label_match(ncit, neuroblastoma):
    """Test that label search resolves to correct record."""
    response = ncit.search('Neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)


def test_alias_match(ncit, neuroblastoma):
    """Test that alias search resolves to correct record."""
    response = ncit.search('neuroblastoma, nos')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('neuroblastoma (Schwannian Stroma-Poor)')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('Neuroblastoma, Malignant')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('Neural Crest Tumor, Malignant')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('neuroblastoma nbl')
    assert response['match_type'] == MatchType.NO_MATCH


def test_meta(ncit):
    """Test that meta field is correct."""
    response = ncit.search('neuroblastoma')
    assert response['meta_'].data_license == 'CC BY 4.0'
    assert response['meta_'].data_license_url == \
        'https://creativecommons.org/licenses/by/4.0/legalcode'
    assert response['meta_'].version == '20.09d'
    assert response['meta_'].data_url == \
        "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/20.09d_Release/"  # noqa: E501
    assert response['meta_'].rdp_url == 'http://reusabledata.org/ncit.html'  # noqa: E501
    assert response['meta_'].data_license_attributes == {
        "non_commercial": False,
        "share_alike": False,
        "attribution": True
    }
