"""Test merged record generation."""

import os
from collections.abc import Callable

import pytest

from disease import SOURCES_FOR_MERGE
from disease.database import AWS_ENV_VAR_NAME
from disease.database.database import create_db
from disease.etl import DO, OMIM, Merge, Mondo, NCIt, OncoTree
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
            msg = f"Running the full disease ETL pipeline test on an AWS environment is forbidden -- either unset {AWS_ENV_VAR_NAME} or unset DISEASE_TEST"
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
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return {
        "concept_id": "ncit:C3270",
        "item_type": "merger",
        "xrefs": ["mondo:0005072", "oncotree:NBL", "DOID:769"],
        "label": "Neuroblastoma",
        "aliases": [
            "NB",
            "neuroblastoma",
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "Neuroblastoma, NOS",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma (NBL)",
            "neural Crest tumor, malignant",
            "neuroblastoma, malignant",
        ],
        "associated_with": [
            "efo:0000621",
            "gard:7185",
            "icdo:9500/3",
            "mesh:D009447",
            "medgen:18012",
            "orphanet:635",
            "umls:C0027819",
            "umls:C2751421",
        ],
        "oncologic_disease": True,
    }


@pytest.fixture(scope="module")
def lnscc():
    """Create lung non small cell carcinoma fixture"""
    return {
        "concept_id": "ncit:C2926",
        "xrefs": ["mondo:0005233", "oncotree:NSCLC", "DOID:3908"],
        "label": "Lung Non-Small Cell Carcinoma",
        "aliases": [
            "NSCLC - Non-Small Cell Lung Cancer",
            "NSCLC - non-small cell lung cancer",
            "NSCLC",
            "Non Small Cell Lung Cancer NOS",
            "Non-Small Cell Cancer of Lung",
            "Non-Small Cell Cancer of the Lung",
            "Non-Small Cell Carcinoma of Lung",
            "Non-Small Cell Carcinoma of the Lung",
            "Non-Small Cell Lung Cancer",
            "Non-Small Cell Lung Carcinoma",
            "Non-small cell lung cancer",
            "Non-small cell lung cancer, NOS",
            "non-small cell cancer of lung",
            "non-small cell cancer of the lung",
            "non-small cell carcinoma of lung",
            "non-small cell carcinoma of the lung",
            "non-small cell lung cancer",
            "non-small cell lung carcinoma (disease)",
            "non-small cell lung carcinoma",
        ],
        "associated_with": [
            "umls:C0007131",
            "mesh:D002289",
            "efo:0003060",
            "kegg.disease:05223",
            "medgen:40104",
        ],
        "item_type": "merger",
        "oncologic_disease": True,
    }


@pytest.fixture(scope="module")
def richter():
    """Create Richter Syndrome fixture"""
    return {
        "concept_id": "ncit:C35424",
        "xrefs": ["mondo:0002083", "DOID:1703"],
        "label": "Richter Syndrome",
        "aliases": [
            "Richter's Syndrome",
            "Richter syndrome",
            "Richter transformation",
            "Richter's Transformation",
            "Richter's syndrome",
            "Richter's transformation",
        ],
        "associated_with": [
            "umls:C0349631",
            "gard:7578",
            "icd10.cm:C91.1",
            "medgen:91159",
        ],
        "item_type": "merger",
        "oncologic_disease": True,
    }


@pytest.fixture(scope="module")
def ped_liposarcoma():
    """Create pediatric liposarcoma fixture."""
    return {
        "concept_id": "ncit:C8091",
        "xrefs": ["mondo:0003587", "DOID:5695"],
        "label": "Childhood Liposarcoma",
        "aliases": [
            "liposarcoma",
            "Liposarcoma",
            "Pediatric Liposarcoma",
            "childhood liposarcoma",
            "pediatric liposarcoma",
        ],
        "associated_with": ["umls:C0279984", "medgen:83580"],
        "pediatric_disease": True,
        "oncologic_disease": True,
        "item_type": "merger",
    }


@pytest.fixture(scope="module")
def teratoma():
    """Create fixture for adult cystic teratoma."""
    return {
        "concept_id": "ncit:C9012",
        "xrefs": ["mondo:0004099", "DOID:7079"],
        "label": "Adult Cystic Teratoma",
        "aliases": [
            "Adult cystic teratoma",
            "cystic teratoma of adults",
            "adult cystic teratoma",
        ],
        "associated_with": ["icdo:9080/0", "umls:C1368888", "medgen:235084"],
        "item_type": "merger",
        "oncologic_disease": True,
    }


@pytest.fixture(scope="module")
def mafd2():
    """Create a fixture for major affective disorder 2. Tests whether a
    deprecated DO reference is filtered out.
    """
    return {
        "item_type": "merger",
        "concept_id": "mondo:0010648",
        "label": "major affective disorder 2",
        "aliases": [
            "BIPOLAR AFFECTIVE DISORDER",
            "BPAD",
            "MAFD2",
            "MANIC-DEPRESSIVE ILLNESS",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "MDI",
            "MDX",
            "major affective disorder 2, X-linked dominant",
            "MAJOR affective disorder 2",
            "bipolar affective disorder",
            "major affective disorder 2",
            "manic-depressive illness",
            "manic-depressive psychosis, X-linked",
        ],
        "xrefs": [
            "MIM:309200",
        ],
        "associated_with": ["mesh:C564108", "medgen:326975", "umls:C1839839"],
    }


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
