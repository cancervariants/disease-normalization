"""Test merged record generation."""

import os
from collections.abc import Callable

import deepdiff
import pytest
from ga4gh.core.models import MappableConcept

from disease.database import AWS_ENV_VAR_NAME, AbstractDatabase
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


@pytest.fixture
def mock_db(
    mock_db_class: type[AbstractDatabase], diseases: dict[str, MappableConcept]
) -> AbstractDatabase:
    return mock_db_class(get_record_by_id=diseases)


def test_generate_merged_record(
    mock_db: AbstractDatabase,
    merged_diseases: dict[str, MappableConcept],
    merged_groups: dict[str, list[str]],
):
    """Test generation of individual merged record."""
    for key_id, ids_group in merged_groups.items():
        m = Merge(mock_db)
        results = m._generate_merged_record(set(ids_group))
        assert set(results[1]) == set(ids_group)
        expected = merged_diseases[key_id]
        diff = deepdiff.DeepDiff(
            results[0], expected, ignore_order=True, report_repetition=True
        )
        assert not diff, diff.pretty()
