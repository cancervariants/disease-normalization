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

# IS_DDB = not get_config().db_url.lower().startswith("postgres")
IS_TEST_ENV = get_config().test


# def test_schema_initialized(database: AbstractDatabase) -> None:
#     """Check that the database schema is initialized."""
#     assert database.check_schema_initialized()
#
#
# def test_tables_populated(database: AbstractDatabase) -> None:
#     """Check that required tables are populated."""
#     assert database.check_tables_populated()
#
#
# def test_tables_created(database):
#     """Check that required tables are created."""
#     existing_tables = database.list_tables()
#     if database.__class__.__name__ == "PostgresDatabase":
#         assert set(existing_tables) == {
#             "disease_associations",
#             "disease_labels",
#             "disease_aliases",
#             "disease_xrefs",
#             "disease_concepts",
#             "disease_merged",
#             "disease_sources",
#         }
#     else:
#         assert database.disease_table in existing_tables
#
#
# @pytest.mark.skipif(not IS_DDB, reason="only applies to DynamoDB in test env")
# def test_item_type(database):
#     """Check that objects are tagged with item_type attribute."""
#     from boto3.dynamodb.conditions import Key
#
#     filter_exp = Key("label_and_type").eq("ncit:c2926##identity")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "identity"
#
#     filter_exp = Key("label_and_type").eq("neuroblastoma##label")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "label"
#
#     filter_exp = Key("label_and_type").eq("umls:c0027819##associated_with")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "associated_with"
#
#     filter_exp = Key("label_and_type").eq("oncotree:nbl##xref")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "xref"
#
#     filter_exp = Key("label_and_type").eq("childhood liposarcoma##alias")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "alias"
#
#     filter_exp = Key("label_and_type").eq("ncit:c9012##merger")
#     item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
#     assert "item_type" in item
#     assert item["item_type"] == "merger"
#
#
# @pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
# def database(db_fixture):
#     """Perform basic test of get_all_records method.
#
#     It's probably overkill (and unmaintainable) to do exact checks against every
#     record, but fairly easy to check against expected counts and ensure that nothing
#     is getting sent twice.
#     """
#     source_records = list(db_fixture.get_all_records(RecordType.IDENTITY))
#     assert len(source_records) == 1463
#     source_ids = {r["concept_id"] for r in source_records}
#     assert len(source_ids) == 1463
#
#     normalized_records = list(db_fixture.get_all_records(RecordType.MERGER))
#     assert len(normalized_records) == 1391
#     normalized_ids = {r["concept_id"] for r in normalized_records}
#     assert len(normalized_ids) == 1391


@pytest.fixture
def db() -> AbstractDatabase:
    db_instance = create_db()
    try:
        db_instance.drop_db()
        db_instance.initialize_db()
        yield db_instance
    finally:
        db_instance.drop_db()


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_crud_source_metadata(
    db: AbstractDatabase, datasets: dict[SourceName, DataSet]
):
    for name in SourceName:
        db.add_source_metadata(name, datasets[name])

    for name in SourceName:
        result = db.get_source_metadata(name)
        expected = datasets[name]

        # TODO
        # these checks are preliminary -- should check for exact equality once API migration is done
        assert result.version == expected.version
        assert result.data_license == expected.license.name
        assert result.data_license_url == expected.license.primaryCoding.iris[0].root


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_crud_source_records(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    datasets: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, datasets[name])
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
    datasets: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, datasets[name])
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
    datasets: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, datasets[name])
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
    datasets: dict[SourceName, DataSet],
):
    for name in SourceName:
        db.add_source_metadata(name, datasets[name])
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
    assert set(results) == {"ncit:C2926", "mondo:0005233", "oncotree:NSCLC"}
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
    assert set(results) == {"DOID:1703", "mondo:0002083"}


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_merged_crud(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    datasets: dict[SourceName, DataSet],
):
    # TODO test add_merged_record, update_merge_ref
    ...


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def test_delete_source(
    db: AbstractDatabase,
    diseases: dict[str, MappableConcept],
    datasets: dict[SourceName, DataSet],
):
    # TODO add all records,
    # then iteratively delete sources and check stuff still works
    ...
