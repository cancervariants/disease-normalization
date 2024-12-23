"""Test Oncotree ETL methods."""

import re

import pytest

from disease.etl.oncotree import OncoTree
from disease.schemas import Disease, MatchType


@pytest.fixture(scope="module")
def oncotree(test_source):
    """Build OncoTree ETL test fixture."""
    return test_source(OncoTree)


@pytest.fixture(scope="module")
def neuroblastoma():
    """Return neuroblastoma test fixture."""
    return Disease(
        label="Neuroblastoma",
        concept_id="oncotree:NBL",
        aliases=[],
        xrefs=["ncit:C3270"],
        associated_with=["umls:C0027819"],
        pediatric_disease=None,
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def nsclc():
    """Return non small cell lung cancer fixture"""
    return Disease(
        label="Non-Small Cell Lung Cancer",
        concept_id="oncotree:NSCLC",
        aliases=[],
        xrefs=["ncit:C2926"],
        associated_with=["umls:C0007131"],
        pediatric_disease=None,
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def ipn():
    """Return fixture for intracholecystic papillary neoplasm"""
    return Disease(
        label="Intracholecystic Papillary Neoplasm",
        concept_id="oncotree:ICPN",
        aliases=[],
        xrefs=[],
        associated_with=[],
        pediatric_disease=None,
        oncologic_disease=True,
    )


def test_concept_id_match(oncotree, neuroblastoma, nsclc, ipn, compare_response):
    """Test that concept ID search resolves to correct record"""
    response = oncotree.search("oncotree:NBL")
    compare_response(response, MatchType.CONCEPT_ID, neuroblastoma)

    response = oncotree.search("oncotree:NSCLC")
    compare_response(response, MatchType.CONCEPT_ID, nsclc)

    response = oncotree.search("oncotree:icpn")
    compare_response(response, MatchType.CONCEPT_ID, ipn)

    response = oncotree.search("oncotree:ICPN")
    compare_response(response, MatchType.CONCEPT_ID, ipn)

    response = oncotree.search("ipn")
    assert response.match_type == MatchType.NO_MATCH


def test_label_match(oncotree, neuroblastoma, nsclc, ipn, compare_response):
    """Test that label search resolves to correct record."""
    response = oncotree.search("Neuroblastoma")
    compare_response(response, MatchType.LABEL, neuroblastoma)

    response = oncotree.search("NEUROBLASTOMA")
    compare_response(response, MatchType.LABEL, neuroblastoma)

    response = oncotree.search("non-small cell lung cancer")
    compare_response(response, MatchType.LABEL, nsclc)

    response = oncotree.search("intracholecystic papillary neoplasm")
    compare_response(response, MatchType.LABEL, ipn)


def test_associated_with_match(oncotree, neuroblastoma, nsclc, compare_response):
    """Test that associated_with search resolves to correct record."""
    response = oncotree.search("umls:c0027819")
    compare_response(response, MatchType.ASSOCIATED_WITH, neuroblastoma)

    response = oncotree.search("umls:C0007131")
    compare_response(response, MatchType.ASSOCIATED_WITH, nsclc)


def test_meta(oncotree):
    """Test that meta field is correct."""
    response = oncotree.search("neuroblastoma")
    assert response.source_meta_.data_license == "CC BY 4.0"
    assert (
        response.source_meta_.data_license_url
        == "https://creativecommons.org/licenses/by/4.0/legalcode"
    )
    assert re.match(r"\d\d\d\d\d\d\d\d", response.source_meta_.version)
    assert response.source_meta_.data_url == "http://oncotree.mskcc.org/#/home?tab=api"
    assert response.source_meta_.rdp_url is None
    assert not response.source_meta_.data_license_attributes.non_commercial
    assert not response.source_meta_.data_license_attributes.share_alike
    assert response.source_meta_.data_license_attributes.attribution
