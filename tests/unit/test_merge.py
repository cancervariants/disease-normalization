"""Test merged record generation."""

import os
from collections.abc import Callable

import pytest

from disease.database import AWS_ENV_VAR_NAME
from disease.database.database import create_db
from disease.etl import DO, OMIM, Merge, Mondo, NCIt, OncoTree
from disease.etl.base import SOURCES_FOR_MERGE
from disease.schemas import SourceName


@pytest.fixture(scope="module")
def merge_instance(test_source: Callable, is_test_env: bool):
    """Provide fixture for ETL merge class.

    If in a test environment (e.g. CI) this method will attempt to load any missing
    source data, and then perform merged record generation.
    """
    database = create_db()
    if is_test_env:
        if os.environ.get(AWS_ENV_VAR_NAME):
            msg = f"Running the full disease ETL pipeline test on an AWS environment is forbidden -- either unset {AWS_ENV_VAR_NAME} or unset DISEASE_NORM_TEST"
            raise AssertionError(msg)
        for SourceClass in (Mondo, DO, NCIt, OncoTree, OMIM):  # noqa: N806
            if not database.get_source_metadata(SourceName(SourceClass.__name__)):
                test_source(SourceClass)

    m = Merge(database)
    if is_test_env:
        concept_ids = set()
        for source in SOURCES_FOR_MERGE:
            concept_ids |= database.get_all_concept_ids(source)
        m.create_merged_concepts(concept_ids)
    return m


@pytest.fixture(scope="module")
def record_id_groups():
    """Fixture for concept ID group input."""
    return {
        "neuroblastoma": ["ncit:C3270", "mondo:0005072", "DOID:769", "oncotree:NBL"],
        "lnscc": ["ncit:C2926", "mondo:0005233", "DOID:3908", "oncotree:NSCLC"],
        "richter": ["ncit:C35424", "mondo:0002083", "DOID:1703"],
        "ped_liposarcoma": ["ncit:C8091", "mondo:0003587", "DOID:5695"],
        "teratoma": ["ncit:C9012", "mondo:0004099", "DOID:7079"],
        "mafd2": ["mondo:0010648", "MIM:309200"],
    }


def compare_merged_records(actual, fixture):
    """Verify correctness of merged DB record."""
    assert actual["concept_id"] == fixture["concept_id"]
    assert ("xrefs" in actual) == ("xrefs" in fixture)
    if "xrefs" in actual:
        assert set(actual["xrefs"]) == set(fixture["xrefs"])

    assert ("label" in actual) == ("label" in fixture)
    if "label" in actual or "label" in fixture:
        assert actual["label"] == fixture["label"]

    assert ("aliases" in actual) == ("aliases" in fixture)
    if "aliases" in actual or "aliases" in fixture:
        assert set(actual["aliases"]) == set(fixture["aliases"])

    assert ("associated_with" in actual) == ("associated_with" in fixture)
    if "associated_with" in actual or "associated_with" in fixture:
        assert set(actual["associated_with"]) == set(fixture["associated_with"])

    assert ("pediatric_disease" in actual) == ("pediatric_disease" in fixture)
    if "pediatric_disease" in actual or "pediatric_disease" in fixture:
        assert actual["pediatric_disease"] == fixture["pediatric_disease"]

    assert ("oncologic_disease" in actual) == ("oncologic_disease" in fixture)
    if "oncologic_disease" in actual or "oncologic_disease" in fixture:
        assert actual["oncologic_disease"] == fixture["oncologic_disease"]


def test_generate_merged_record(
    merge_instance,
    record_id_groups,
    neuroblastoma,
    lnscc,
    richter,
    ped_liposarcoma,
    teratoma,
    mafd2,
):
    """Test generation of individual merged record."""
    neuroblastoma_ids = record_id_groups["neuroblastoma"]
    response, r_ids = merge_instance._generate_merged_record(neuroblastoma_ids)
    assert set(r_ids) == set(neuroblastoma_ids)
    compare_merged_records(response, neuroblastoma)

    lnscc_ids = record_id_groups["lnscc"]
    response, r_ids = merge_instance._generate_merged_record(lnscc_ids)
    assert set(r_ids) == set(lnscc_ids)
    compare_merged_records(response, lnscc)

    richter_ids = record_id_groups["richter"]
    response, r_ids = merge_instance._generate_merged_record(richter_ids)
    assert set(r_ids) == set(richter_ids)
    compare_merged_records(response, richter)

    ped_liposarcoma_ids = record_id_groups["ped_liposarcoma"]
    response, r_ids = merge_instance._generate_merged_record(ped_liposarcoma_ids)
    assert set(r_ids) == set(ped_liposarcoma_ids)
    compare_merged_records(response, ped_liposarcoma)

    teratoma_ids = record_id_groups["teratoma"]
    response, r_ids = merge_instance._generate_merged_record(teratoma_ids)
    assert set(r_ids) == set(teratoma_ids)
    compare_merged_records(response, teratoma)

    mafd2_ids = record_id_groups["mafd2"]
    response, r_ids = merge_instance._generate_merged_record(mafd2_ids)
    assert set(r_ids) == {"mondo:0010648", "MIM:309200"}
    compare_merged_records(response, mafd2)
