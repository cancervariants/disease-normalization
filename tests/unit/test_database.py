"""Test database classes.

A lot of these tests are slightly more roundabout than they need to be until the
migration to VA-Spec for everything is complete.
"""

from collections import defaultdict

import pytest
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.config import get_config
from disease.database import create_db
from disease.database.database import AbstractDatabase
from disease.schemas import (
    PREFIX_LOOKUP,
    RecordType,
    RefType,
    SourceName,
    coding_to_concept_id,
    mapcon_to_disease,
)

IS_DDB = not get_config().db_url.lower().startswith("postgres")
IS_TEST_ENV = get_config().test


@pytest.fixture
def db() -> AbstractDatabase:
    """A real live db instance (gets overwritten immediately)"""
    db_instance = create_db()
    try:
        db_instance.drop_db()
        db_instance.initialize_db()
        yield db_instance
    finally:
        db_instance.drop_db()


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_db_healthchecks(
    db: AbstractDatabase,
    sources: dict[SourceName, DataSet],
    diseases: dict[str, MappableConcept],
    merged_diseases: dict[str, MappableConcept],
):
    # this should always pass here but just double-checking
    assert db.check_schema_initialized(), "schema appears un-initialized"
    # db should be empty
    db.drop_db()
    db.initialize_db()
    assert db.check_schema_initialized(), "schema failed to initialize"
    assert not db.check_tables_populated(), "db should be empty here"

    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))
    for record in merged_diseases.values():
        db.add_merged_record(record)

    assert db.check_tables_populated(), "db should be populated"


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_crud_source_metadata(db: AbstractDatabase, sources: dict[SourceName, DataSet]):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])

    for name in SourceName:
        result = db.get_source_metadata(name)
        expected = sources[name]

        # TODO:
        # these checks are preliminary -- should check for exact equality once API migration is done
        assert result.version == expected.version
        assert result.data_license == expected.license.name
        assert result.data_license_url == expected.license.primaryCoding.iris[0].root


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_crud_source_records(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))

    for concept_id, disease_mapcon in diseases.items():
        expected = mapcon_to_disease(disease_mapcon).model_dump()
        expected["merge_ref"] = None
        expected["src_name"] = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        expected["item_type"] = "identity"
        result = db.get_record_by_id(concept_id)
        assert result == expected

    # check case sensitivity
    for concept_id, disease_mapcon in diseases.items():
        expected = mapcon_to_disease(disease_mapcon).model_dump()
        expected["merge_ref"] = None
        expected["src_name"] = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        expected["item_type"] = "identity"
        result = db.get_record_by_id(concept_id.lower(), case_sensitive=False)
        assert result == expected

        result = db.get_record_by_id(concept_id.upper(), case_sensitive=False)
        assert result == expected


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_get_all_concept_ids(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))

    # all sources
    result = db.get_all_concept_ids()
    assert result == set(diseases)

    # by source
    grouped = defaultdict(set)
    for curie in diseases:
        prefix = curie.split(":", 1)[0]
        grouped[prefix].add(curie)
    for src_prefix, concept_ids in grouped.items():
        src = PREFIX_LOOKUP[src_prefix.lower()]
        result = db.get_all_concept_ids(src)
        assert set(result) == concept_ids


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_get_all_records(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))

    result = list(db.get_all_records(RecordType.IDENTITY))
    assert len(result) == len(diseases)
    assert {r["concept_id"] for r in result} == set(diseases)


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_get_all_merged_records(
    db: AbstractDatabase,
    merged_diseases: dict[str, MappableConcept],
):
    for record in merged_diseases.values():
        db.add_merged_record(record)

    results = list(db.get_all_records(RecordType.MERGER))
    assert len(results) == len(merged_diseases)
    grouped_results = {r["concept_id"]: r for r in results}
    for merged_disease in merged_diseases.values():
        key_id = coding_to_concept_id(merged_disease.primaryCoding)
        expected = mapcon_to_disease(merged_disease).model_dump(exclude_none=True)
        expected["item_type"] = RecordType.MERGER.value
        assert grouped_results[key_id] == expected


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_get_refs_by_type(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))

    # label
    results = db.get_refs_by_type("neuroblastoma", RefType.LABEL)
    assert set(results) == {"oncotree:NBL", "DOID:769", "mondo:0005072", "ncit:C3270"}
    results = db.get_refs_by_type("Intracholecystic Papillary Neoplasm", RefType.LABEL)
    assert set(results) == {"oncotree:ICPN"}

    # alias
    results = db.get_refs_by_type("nsclc", RefType.ALIASES)
    assert set(results) == {
        "ncit:C2926",
        "mondo:0005233",
        "oncotree:NSCLC",
        "DOID:3908",
    }
    results = db.get_refs_by_type("MAFD2", RefType.ALIASES)
    assert set(results) == {"MIM:309200"}

    # xrefs
    results = db.get_refs_by_type("ncit:C3270", RefType.XREFS)
    assert set(results) == {"oncotree:NBL", "DOID:769", "mondo:0005072"}
    results = db.get_refs_by_type("DOID:5695", RefType.XREFS)
    assert set(results) == {"mondo:0003587"}

    # assoc with
    results = db.get_refs_by_type("orphanet:635", RefType.ASSOCIATED_WITH)
    assert set(results) == {"DOID:769", "mondo:0005072"}
    results = db.get_refs_by_type("umls:C0349631", RefType.ASSOCIATED_WITH)
    assert set(results) == {"DOID:1703", "mondo:0002083", "ncit:C35424"}


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_merged_crud(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    merged_diseases: dict[str, MappableConcept],
    merged_groups: dict[str, list[str]],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))
    for merged_id, merged_disease in merged_diseases.items():
        db.add_merged_record(merged_disease)
        for grp_member_id in merged_groups[merged_id]:
            db.update_merge_ref(grp_member_id, merged_id)

    for merged_id in merged_diseases:
        for grp_member_id in merged_groups[merged_id]:
            result = db.get_record_by_id(grp_member_id)
            assert result["merge_ref"] == merged_id


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_delete_source(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, sources[name])
    for concept_id, disease in diseases.items():
        src_name = PREFIX_LOOKUP[concept_id.split(":", 1)[0].lower()]
        db.add_record(disease, SourceName(src_name))

    assert db.get_record_by_id("DOID:769")
    assert db.get_record_by_id("oncotree:NBL")
    assert db.get_record_by_id("mondo:0005072")
    assert db.get_record_by_id("ncit:C3270")
    assert db.get_record_by_id("MIM:613065")
    db.delete_source(SourceName.OMIM)
    assert db.get_record_by_id("DOID:769")
    assert db.get_record_by_id("oncotree:NBL")
    assert db.get_record_by_id("mondo:0005072")
    assert db.get_record_by_id("ncit:C3270")
    assert not db.get_record_by_id("MIM:613065")
    db.delete_source(SourceName.NCIT)
    db.delete_source(SourceName.NCIT)  # check idempotency, why not
    assert db.get_record_by_id("DOID:769")
    assert db.get_record_by_id("oncotree:NBL")
    assert db.get_record_by_id("mondo:0005072")
    assert not db.get_record_by_id("ncit:C3270")
    assert not db.get_record_by_id("MIM:613065")
    db.delete_source(SourceName.MONDO)
    assert db.get_record_by_id("DOID:769")
    assert db.get_record_by_id("oncotree:NBL")
    assert not db.get_record_by_id("mondo:0005072")
    assert not db.get_record_by_id("ncit:C3270")
    assert not db.get_record_by_id("MIM:613065")
    db.delete_source(SourceName.ONCOTREE)
    assert db.get_record_by_id("DOID:769")
    assert not db.get_record_by_id("oncotree:NBL")
    assert not db.get_record_by_id("mondo:0005072")
    assert not db.get_record_by_id("ncit:C3270")
    assert not db.get_record_by_id("MIM:613065")
    db.delete_source(SourceName.DO)
    assert not db.get_record_by_id("DOID:769")
    assert not db.get_record_by_id("oncotree:NBL")
    assert not db.get_record_by_id("mondo:0005072")
    assert not db.get_record_by_id("ncit:C3270")
    assert not db.get_record_by_id("MIM:613065")
