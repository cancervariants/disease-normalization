"""Test NCIt source."""
import re

import pytest

from disease.schemas import MatchType, SourceName, Disease
from disease.query import QueryHandler


@pytest.fixture(scope='module')
def ncit():
    """Build NCIt ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search(query_str, keyed=True,
                                                 incl="ncit")
            return response.source_matches[SourceName.NCIT]
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Build neuroblastoma test fixture."""
    return Disease(**{
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
        "xrefs": [],
        "associated_with": ["umls:C2751421", "icdo:9500/3"],
        "src_name": "NCIt"
    })


@pytest.fixture(scope='module')
def nsclc():
    """Build fixture for non-small cell lung carcinoma"""
    return Disease(**{
        "concept_id": "ncit:C2926",
        "label": "Lung Non-Small Cell Carcinoma",
        "aliases": [
            "Non Small Cell Lung Cancer NOS",
            "Non-Small Cell Lung Cancer",
            "Non-Small Cell Cancer of the Lung",
            "NSCLC",
            "non-small cell lung cancer",
            "Non-Small Cell Carcinoma of the Lung",
            "Non-Small Cell Cancer of Lung",
            "Non-small cell lung cancer, NOS",
            "Non-Small Cell Carcinoma of Lung",
            "NSCLC - Non-Small Cell Lung Cancer",
            "Non-Small Cell Lung Carcinoma"
        ],
        "xrefs": [],
        "associated_with": ["umls:C0007131"]
    })


def test_concept_id_match(ncit, neuroblastoma, nsclc, compare_records):
    """Test that concept ID search resolves to correct record"""
    response = ncit.search('ncit:C3270')
    assert response.match_type == MatchType.CONCEPT_ID
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('ncit:c2926')
    assert response.match_type == MatchType.CONCEPT_ID
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = ncit.search('NCIT:C2926')
    assert response.match_type == MatchType.CONCEPT_ID
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = ncit.search('C3270')
    assert response.match_type == MatchType.CONCEPT_ID
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('3270')
    assert response.match_type == MatchType.NO_MATCH


def test_label_match(ncit, neuroblastoma, nsclc, compare_records):
    """Test that label search resolves to correct record."""
    response = ncit.search('Neuroblastoma')
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('NEUROBLASTOMA')
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('lung non-small cell carcinoma')
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = ncit.search('lung non small cell carcinoma')
    assert response.match_type == MatchType.NO_MATCH


def test_alias_match(ncit, neuroblastoma, nsclc, compare_records):
    """Test that alias search resolves to correct record."""
    response = ncit.search('neuroblastoma, nos')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('neuroblastoma (Schwannian Stroma-Poor)')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('Neuroblastoma, Malignant')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('Neural Crest Tumor, Malignant')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('nsclc')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = ncit.search('NSCLC - Non-Small Cell Lung Cancer')
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = ncit.search('neuroblastoma nbl')
    assert response.match_type == MatchType.NO_MATCH


def test_associated_with_match(ncit, neuroblastoma, nsclc, compare_records):
    """Test that associated_with search resolves to correct record."""
    response = ncit.search('icdo:9500/3')
    assert response.match_type == MatchType.ASSOCIATED_WITH
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = ncit.search('umls:C0007131')
    assert response.match_type == MatchType.ASSOCIATED_WITH
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)


def test_meta(ncit):
    """Test that meta field is correct."""
    response = ncit.search('neuroblastoma')
    assert response.source_meta_.data_license == 'CC BY 4.0'
    assert response.source_meta_.data_license_url == \
        'https://creativecommons.org/licenses/by/4.0/legalcode'
    assert re.match(r"\d{2}\.\d{2}[a-z]", response.source_meta_.version)

    assert response.source_meta_.data_url == \
        "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/"
    assert response.source_meta_.rdp_url == 'http://reusabledata.org/ncit.html'
    assert response.source_meta_.data_license_attributes == {
        "non_commercial": False,
        "share_alike": False,
        "attribution": True
    }
