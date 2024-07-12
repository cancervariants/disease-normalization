"""Test database classes."""

import os

import pytest

from disease.schemas import RecordType

IS_DDB = not os.environ.get("DISEASE_NORM_DB_URL", "").lower().startswith("postgres")
IS_TEST_ENV = os.environ.get("DISEASE_TEST", "").lower() == "true"


def test_tables_created(database):
    """Check that required tables are created."""
    existing_tables = database.list_tables()
    if database.__class__.__name__ == "PostgresDatabase":
        assert set(existing_tables) == {
            "disease_associations",
            "disease_labels",
            "disease_aliases",
            "disease_xrefs",
            "disease_concepts",
            "disease_merged",
            "disease_sources",
        }
    else:
        assert database.disease_table in existing_tables


@pytest.mark.skipif(not IS_DDB, reason="only applies to DynamoDB in test env")
def test_item_type(database):
    """Check that objects are tagged with item_type attribute."""
    from boto3.dynamodb.conditions import Key

    filter_exp = Key("label_and_type").eq("ncit:c2926##identity")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "identity"

    filter_exp = Key("label_and_type").eq("neuroblastoma##label")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "label"

    filter_exp = Key("label_and_type").eq("umls:c0027819##associated_with")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "associated_with"

    filter_exp = Key("label_and_type").eq("oncotree:nbl##xref")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "xref"

    filter_exp = Key("label_and_type").eq("childhood liposarcoma##alias")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "alias"

    filter_exp = Key("label_and_type").eq("ncit:c9012##merger")
    item = database.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "merger"


@pytest.mark.skipif(not IS_TEST_ENV, reason="not in test environment")
def database(db_fixture):
    """Perform basic test of get_all_records method.

    It's probably overkill (and unmaintainable) to do exact checks against every
    record, but fairly easy to check against expected counts and ensure that nothing
    is getting sent twice.
    """
    source_records = list(db_fixture.get_all_records(RecordType.IDENTITY))
    assert len(source_records) == 1463
    source_ids = {r["concept_id"] for r in source_records}
    assert len(source_ids) == 1463

    normalized_records = list(db_fixture.get_all_records(RecordType.MERGER))
    assert len(normalized_records) == 1391
    normalized_ids = {r["concept_id"] for r in normalized_records}
    assert len(normalized_ids) == 1391
