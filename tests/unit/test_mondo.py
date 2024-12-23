"""Test MONDO ETL methods."""

import re

import pytest

from disease.etl.mondo import Mondo
from disease.schemas import Disease, MatchType


@pytest.fixture(scope="module")
def mondo(test_source):
    """Build Mondo ETL test fixture."""
    return test_source(Mondo)


@pytest.fixture(scope="module")
def neuroblastoma():
    """Construct a test fixture for neuroblastoma"""
    return Disease(
        concept_id="mondo:0005072",
        label="neuroblastoma",
        aliases=[
            "NB",
            "neuroblastoma",
            "neural Crest tumor, malignant",
            "neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma, malignant",
        ],
        xrefs=[
            "ncit:C3270",
            "DOID:769",
            "oncotree:NBL",
        ],
        associated_with=[
            "orphanet:635",
            "umls:C0027819",
            "efo:0000621",
            "mesh:D009447",
            "medgen:18012",
        ],
        pediatric_disease=None,
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def richter_syndrome():
    """Construct a test fixture for Richter Syndrome"""
    return Disease(
        concept_id="mondo:0002083",
        label="Richter syndrome",
        aliases=[
            "Richter syndrome",
            "Richter's syndrome",
            "Richter transformation",
            "Richter's transformation",
        ],
        xrefs=["ncit:C35424", "DOID:1703"],
        associated_with=["umls:C0349631", "medgen:91159"],
        pediatric_disease=None,
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def pediatric_liposarcoma():
    """Construct a test fixture for pediatric liposarcoma. Tests the
    pediatric flag.
    """
    return Disease(
        concept_id="mondo:0003587",
        label="pediatric liposarcoma",
        aliases=[
            "pediatric liposarcoma",
            "childhood liposarcoma",
            "liposarcoma",
        ],
        xrefs=["DOID:5695", "ncit:C8091"],
        associated_with=["umls:C0279984", "medgen:83580"],
        pediatric_disease=True,
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def cystic_teratoma_adult():
    """Construct a test fixture for adult cystic teratoma. Tests the
    pediatric flag.
    """
    return Disease(
        concept_id="mondo:0004099",
        label="adult cystic teratoma",
        aliases=["cystic teratoma of adults", "adult cystic teratoma"],
        pediatric_disease=None,
        xrefs=["ncit:C9012", "DOID:7079"],
        associated_with=["umls:C1368888", "medgen:235084"],
        oncologic_disease=True,
    )


@pytest.fixture(scope="module")
def nsclc():
    """Construct a test fixture for non small cell lung cancer."""
    return Disease(
        concept_id="mondo:0005233",
        label="non-small cell lung carcinoma",
        aliases=[
            "NSCLC - non-small cell lung cancer",
            "non-small cell lung carcinoma (disease)",
            "non-small cell carcinoma of lung",
            "non-small cell carcinoma of the lung",
            "non-small cell cancer of lung",
            "non-small cell lung cancer",
            "non-small cell cancer of the lung",
            "NSCLC",
            "non-small cell lung carcinoma",
        ],
        xrefs=["ncit:C2926", "oncotree:NSCLC", "DOID:3908"],
        associated_with=[
            "mesh:D002289",
            "umls:C0007131",
            "efo:0003060",
            "medgen:40104",
        ],
        oncologic_disease=True,
    )


def test_neuroblastoma(mondo, neuroblastoma, compare_response, compare_records):
    response = mondo.search("MONDO:0005072")
    compare_response(response, MatchType.CONCEPT_ID, neuroblastoma)

    response = mondo.search("Neuroblastoma")
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("NEUROBLASTOMA")
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("neuroblastoma, malignant")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("DOID:769")
    assert response.match_type == MatchType.XREF
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("orphanet:635")
    assert response.match_type == MatchType.ASSOCIATED_WITH
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("Neuroblastoma, Malignant")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("neuroblastoma (Schwannian Stroma-poor)")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, neuroblastoma)


def test_richter_syndrome(mondo, richter_syndrome, compare_records, compare_response):
    response = mondo.search("mondo:0002083")
    compare_response(response, MatchType.CONCEPT_ID, richter_syndrome)

    response = mondo.search("richter syndrome")
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("umls:C0349631")
    assert response.match_type == MatchType.ASSOCIATED_WITH
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("RICHTER TRANSFORMATION")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("Richter's transformation")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("Richter's syndrome")
    assert response.match_type == MatchType.ALIAS
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, richter_syndrome)


def test_pediatric_liposarcoma(
    mondo, pediatric_liposarcoma, compare_records, compare_response
):
    response = mondo.search("mondo:0003587")
    compare_response(response, MatchType.CONCEPT_ID, pediatric_liposarcoma)

    response = mondo.search("pediatric liposarcoma")
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, pediatric_liposarcoma)

    response = mondo.search("ncit:c8091")
    assert response.match_type == MatchType.XREF
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, pediatric_liposarcoma)

    response = mondo.search("UMLS:C0279984")
    assert response.match_type == MatchType.ASSOCIATED_WITH
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, pediatric_liposarcoma)


def test_cystic_teratoma_adult(
    mondo,
    cystic_teratoma_adult,
    compare_response,
    compare_records,
):
    response = mondo.search("mondo:0004099")
    compare_response(response, MatchType.CONCEPT_ID, cystic_teratoma_adult)

    response = mondo.search("Adult Cystic Teratoma")
    assert response.match_type == MatchType.LABEL
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, cystic_teratoma_adult)


def test_nsclc(
    mondo,
    nsclc,
    compare_response,
    compare_records,
):
    response = mondo.search("mondo:0005233")
    compare_response(response, MatchType.CONCEPT_ID, nsclc)

    response = mondo.search("oncotree:NSCLC")
    assert response.match_type == MatchType.XREF
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)

    response = mondo.search("ncit:C2926")
    assert response.match_type == MatchType.XREF
    assert len(response.records) == 1
    actual_disease = response.records[0]
    compare_records(actual_disease, nsclc)


def test_meta(mondo):
    """Test that meta field is correct."""
    response = mondo.search("neuroblastoma")
    assert response.source_meta_.data_license == "CC BY 4.0"
    assert (
        response.source_meta_.data_license_url
        == "https://creativecommons.org/licenses/by/4.0/legalcode"
    )
    assert re.match(r"\d{4}\d{2}\d{2}", response.source_meta_.version)
    assert (
        response.source_meta_.data_url
        == "https://mondo.monarchinitiative.org/pages/download/"
    )
    assert response.source_meta_.rdp_url == "http://reusabledata.org/monarch.html"
    assert not response.source_meta_.data_license_attributes.non_commercial
    assert not response.source_meta_.data_license_attributes.share_alike
    assert response.source_meta_.data_license_attributes.attribution
