"""Test DynamoDB"""
import pytest
from disease.database import Database
from disease import PROJECT_ROOT
import json
import os


@pytest.fixture(scope='module')
def db():
    """Create a DynamoDB test fixture."""
    class DB:
        def __init__(self):
            self.db = Database()
            if os.environ.get('TEST') is not None:
                self.load_test_data()

        def load_test_data(self):
            with open(f'{PROJECT_ROOT}/tests/unit/'
                      f'data/diseases.json', 'r') as f:
                diseases = json.load(f)
                with self.db.diseases.batch_writer() as batch:
                    for disease in diseases:
                        batch.put_item(Item=disease)
                f.close()

            with open(f'{PROJECT_ROOT}/tests/unit/'
                      f'data/metadata.json', 'r') as f:
                metadata = json.load(f)
                with self.db.metadata.batch_writer() as batch:
                    for m in metadata:
                        batch.put_item(Item=m)
                f.close()

    return DB()


def test_tables_created(db):
    """Check that disease_concepts and disease_metadata are created."""
    existing_tables = db.db.dynamodb_client.list_tables()['TableNames']
    assert 'disease_concepts' in existing_tables
    assert 'disease_metadata' in existing_tables
