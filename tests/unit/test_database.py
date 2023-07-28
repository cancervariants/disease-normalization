"""Test database classes."""
import os

import pytest


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
        assert database.disease_concepts_table in existing_tables
        assert database.disease_metadata_table in existing_tables


IS_DDB = not os.environ.get("DISEASE_NORM_DB_URL", "").lower().startswith("postgres")


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
