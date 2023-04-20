"""Test DynamoDB"""
from boto3.dynamodb.conditions import Key


def test_tables_created(db):
    """Check that disease_concepts and disease_metadata are created."""
    existing_tables = db.dynamodb_client.list_tables()["TableNames"]
    assert "disease_concepts" in existing_tables
    assert "disease_metadata" in existing_tables


def test_item_type(db):
    """Check that objects are tagged with item_type attribute."""
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
