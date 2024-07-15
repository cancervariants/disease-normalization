"""Test NCIt source."""

import re

import pytest

from disease.etl.ncit import NCIt
from disease.schemas import Disease, MatchType


@pytest.fixture(scope="module")
def ncit(test_source):
    """Build NCIt ETL test fixture."""
    return test_source(NCIt)


@pytest.fixture(scope="module")
def neuroblastoma():
    """Build neuroblastoma test fixture."""
    return Disease(
        label_and_type="ncit:c3270##identity",
        concept_id="ncit:C3270",
        label="Neuroblastoma",
        aliases=[
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (NBL)",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma, NOS",
            "neuroblastoma",
        ],
        xrefs=[],
        associated_with=["umls:C2751421", "icdo:9500/3"],
        src_name="NCIt",
    )


@pytest.fixture(scope="module")
def nsclc():
    """Build fixture for non-small cell lung carcinoma"""
    return Disease(
        concept_id="ncit:C2926",
        label="Lung Non-Small Cell Carcinoma",
        aliases=[
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
            "Non-Small Cell Lung Carcinoma",
        ],
        xrefs=[],
        associated_with=["umls:C0007131"],
    )


def test_concept_id_match(ncit, neuroblastoma, nsclc, compare_response):
    """Test that concept ID search resolves to correct record"""
    response = ncit.search("ncit:C3270")
    compare_response(response, MatchType.CONCEPT_ID, neuroblastoma)

    response = ncit.search("ncit:c2926")
    compare_response(response, MatchType.CONCEPT_ID, nsclc)

    response = ncit.search("NCIT:C2926")
    compare_response(response, MatchType.CONCEPT_ID, nsclc)

    response = ncit.search("C3270")
    compare_response(response, MatchType.CONCEPT_ID, neuroblastoma)

    response = ncit.search("3270")
    assert response.match_type == MatchType.NO_MATCH


def test_label_match(ncit, neuroblastoma, nsclc, compare_response):
    """Test that label search resolves to correct record."""
    response = ncit.search("Neuroblastoma")
    compare_response(response, MatchType.LABEL, neuroblastoma)

    response = ncit.search("NEUROBLASTOMA")
    compare_response(response, MatchType.LABEL, neuroblastoma)

    response = ncit.search("lung non-small cell carcinoma")
    compare_response(response, MatchType.LABEL, nsclc)

    response = ncit.search("lung non small cell carcinoma")
    assert response.match_type == MatchType.NO_MATCH


def test_alias_match(ncit, neuroblastoma, nsclc, compare_response):
    """Test that alias search resolves to correct record."""
    response = ncit.search("neuroblastoma, nos")
    compare_response(response, MatchType.ALIAS, neuroblastoma)

    response = ncit.search("neuroblastoma (Schwannian Stroma-Poor)")
    compare_response(response, MatchType.ALIAS, neuroblastoma)

    response = ncit.search("Neuroblastoma, Malignant")
    compare_response(response, MatchType.ALIAS, neuroblastoma)

    response = ncit.search("Neural Crest Tumor, Malignant")
    compare_response(response, MatchType.ALIAS, neuroblastoma)

    response = ncit.search("nsclc")
    compare_response(response, MatchType.ALIAS, nsclc)

    response = ncit.search("NSCLC - Non-Small Cell Lung Cancer")
    compare_response(response, MatchType.ALIAS, nsclc)

    response = ncit.search("neuroblastoma nbl")
    assert response.match_type == MatchType.NO_MATCH


def test_associated_with_match(ncit, neuroblastoma, nsclc, compare_response):
    """Test that associated_with search resolves to correct record."""
    response = ncit.search("icdo:9500/3")
    compare_response(response, MatchType.ASSOCIATED_WITH, neuroblastoma)

    response = ncit.search("umls:C0007131")
    compare_response(response, MatchType.ASSOCIATED_WITH, nsclc)


def test_meta(ncit):
    """Test that meta field is correct."""
    response = ncit.search("neuroblastoma")
    assert response.source_meta_.data_license == "CC BY 4.0"
    assert (
        response.source_meta_.data_license_url
        == "https://creativecommons.org/licenses/by/4.0/legalcode"
    )
    assert re.match(r"\d{2}\.\d{2}[a-z]", response.source_meta_.version)
    assert (
        response.source_meta_.data_url == "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/"
    )
    assert response.source_meta_.rdp_url == "http://reusabledata.org/ncit.html"
    assert not response.source_meta_.data_license_attributes.non_commercial
    assert not response.source_meta_.data_license_attributes.share_alike
    assert response.source_meta_.data_license_attributes.attribution
