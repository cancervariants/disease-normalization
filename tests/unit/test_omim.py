"""Test OMIM source."""

import re

import pytest

from disease.etl.omim import OMIM
from disease.schemas import Disease, MatchType


@pytest.fixture(scope="module")
def omim(test_source):
    """Build OMIM ETL test fixture."""
    return test_source(OMIM)


@pytest.fixture(scope="module")
def mafd2():
    """Build MAFD2 test fixture."""
    return Disease(
        concept_id="MIM:309200",
        label="MAJOR AFFECTIVE DISORDER 2",
        aliases=[
            "MAFD2",
            "MANIC-DEPRESSIVE ILLNESS",
            "MDI",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "MDX",
            "BIPOLAR AFFECTIVE DISORDER",
            "BPAD",
        ],
        xrefs=[],
        associated_with=[],
        pediatric_disease=None,
        oncologic_disease=None,
    )


@pytest.fixture(scope="module")
def acute_ll():
    """Build ALL fixture."""
    return Disease(
        concept_id="MIM:613065",
        label="LEUKEMIA, ACUTE LYMPHOBLASTIC",
        aliases=[
            "ALL",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO, 1",
            "ALL1",
            "LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1",
            "LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, T-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, B-HYPERDIPLOID, SUSCEPTIBILITY TO",
        ],
        xrefs=[],
        associated_with=[],
        pediatric_disease=None,
        oncologic_disease=None,
    )


@pytest.fixture(scope="module")
def lall():
    """Build LALL fixture."""
    return Disease(
        concept_id="MIM:247640",
        label="LYMPHOBLASTIC LEUKEMIA, ACUTE, WITH LYMPHOMATOUS FEATURES",
        aliases=["LALL", "LYMPHOMATOUS ALL"],
        xrefs=[],
        associated_with=[],
        pediatric_disease=None,
        oncologic_disease=None,
    )


def test_concept_id_match(omim, mafd2, acute_ll, lall, compare_response):
    """Test concept ID search resolution."""
    response = omim.search("MIM:309200")
    compare_response(response, MatchType.CONCEPT_ID, mafd2)

    response = omim.search("MIM:613065")
    compare_response(response, MatchType.CONCEPT_ID, acute_ll)

    response = omim.search("MIM:247640")
    compare_response(response, MatchType.CONCEPT_ID, lall)


def test_label_match(omim, mafd2, acute_ll, lall, compare_response):
    """Test label search resolution."""
    response = omim.search("MAJOR AFFECTIVE DISORDER 2")
    compare_response(response, MatchType.LABEL, mafd2)

    response = omim.search("LEUKEMIA, ACUTE LYMPHOBLASTIC")
    compare_response(response, MatchType.LABEL, acute_ll)

    response = omim.search("lymphoblastic leukemia, acute, with lymphomatous features")
    compare_response(response, MatchType.LABEL, lall)


def test_alias_match(omim, mafd2, acute_ll, lall, compare_response):
    """Test alias search resolution."""
    response = omim.search("manic-depressive psychosis, x-linked")
    compare_response(response, MatchType.ALIAS, mafd2)

    response = omim.search("mafd2")
    compare_response(response, MatchType.ALIAS, mafd2)

    response = omim.search("all")
    compare_response(response, MatchType.ALIAS, acute_ll)

    response = omim.search("LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1")
    compare_response(response, MatchType.ALIAS, acute_ll)

    response = omim.search("LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO")
    compare_response(response, MatchType.ALIAS, acute_ll)

    response = omim.search("lymphomatous all")
    compare_response(response, MatchType.ALIAS, lall)

    response = omim.search("lall")
    compare_response(response, MatchType.ALIAS, lall)


def test_meta(omim):
    """Test that meta field is correct."""
    response = omim.search("irrelevant-search-string")
    assert response.source_meta_.data_license == "custom"
    assert response.source_meta_.data_license_url == "https://omim.org/help/agreement"
    assert re.match(r"\d{4}\d{2}\d{2}", response.source_meta_.version)
    assert response.source_meta_.data_url == "https://www.omim.org/downloads"
    assert response.source_meta_.rdp_url == "http://reusabledata.org/omim.html"
    assert not response.source_meta_.data_license_attributes.non_commercial
    assert response.source_meta_.data_license_attributes.share_alike
    assert response.source_meta_.data_license_attributes.attribution
