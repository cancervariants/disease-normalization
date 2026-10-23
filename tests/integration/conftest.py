from pathlib import Path

import pytest

from disease.database import AbstractDatabase, create_db
from disease.etl import DO, OMIM, Merge, Mondo, NCIt, OncoTree


@pytest.fixture(scope="module")
def db() -> AbstractDatabase:
    """A real live db instance (gets overwritten immediately)

    Different from the DB defined in tests/conftest.py by scope -- this should only
    be written to once during testing
    """
    db_instance = create_db()
    try:
        db_instance.drop_db()
        db_instance.initialize_db()
        yield db_instance
    finally:
        db_instance.drop_db()


@pytest.fixture(scope="module")
def populated_db(db: AbstractDatabase, test_data_dir: Path) -> AbstractDatabase:
    """A database populated using ETL classes and test data inputs"""
    for pathname, etl_source in (
        ("do", DO),
        ("ncit", NCIt),
        ("oncotree", OncoTree),
        ("omim", OMIM),
        ("mondo", Mondo),
    ):
        etl_instance = etl_source(db, test_data_dir / pathname)
        etl_instance.perform_etl(use_existing=True)
    merge = Merge(db)
    concept_ids = db.get_all_concept_ids()
    merge.create_merged_concepts(concept_ids)
    return db
