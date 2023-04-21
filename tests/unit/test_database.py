"""Test DynamoDB"""
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
        assert 'disease_concepts' in existing_tables
        assert 'disease_metadata' in existing_tables


IS_DDB = not os.environ.get("DISEASE_NORM_DB_URL", "").lower().startswith("postgres")


@pytest.mark.skipif(not IS_DDB, reason="only applies to DynamoDB in test env")
def test_item_type(db):
    """Check that objects are tagged with item_type attribute."""
    from boto3.dynamodb.conditions import Key

    filter_exp = Key("label_and_type").eq("ncit:c2926##identity")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "identity"

    filter_exp = Key("label_and_type").eq("neuroblastoma##label")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "label"

    filter_exp = Key("label_and_type").eq("umls:c0027819##associated_with")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "associated_with"

    filter_exp = Key("label_and_type").eq("oncotree:nbl##xref")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "xref"

    filter_exp = Key("label_and_type").eq("childhood liposarcoma##alias")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "alias"

    filter_exp = Key("label_and_type").eq("ncit:c9012##merger")
    item = db.diseases.query(KeyConditionExpression=filter_exp)["Items"][0]
    assert "item_type" in item
    assert item["item_type"] == "merger"
