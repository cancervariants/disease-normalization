"""Test merged record generation."""

import os
from collections.abc import Callable
from unittest.mock import Mock

import deepdiff
import pytest
from ga4gh.core.models import ConceptMapping, MappableConcept, Relation
from ga4gh.va_spec.base import Condition

from disease.database import AWS_ENV_VAR_NAME, AbstractDatabase
from disease.database.database import create_db
from disease.etl import DO, OMIM, Merge, Mondo, NCIt, OncoTree
from disease.etl.base import SOURCES_FOR_MERGE
from disease.schemas import (
    SourceName,
    SssomMapping,
    concept_id_to_coding,
)


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


def test_merge_honors_mapping_negation(diseases):
    subject, target = "mondo:0005072", "ncit:C3270"
    coding = concept_id_to_coding(target)
    original = diseases[subject].model_copy(
        update={
            "mappings": [ConceptMapping(coding=coding, relation=Relation.EXACT_MATCH)]
        }
    )
    negation = ConceptMapping(coding=coding, relation=Relation.EXACT_MATCH)
    broad = ConceptMapping(coding=coding, relation=Relation.BROAD_MATCH)
    corrected = AbstractDatabase._without_negated_mappings(original, [negation])
    augmented = AbstractDatabase._with_supplemental_mappings(corrected, [broad])
    db = Mock(spec=AbstractDatabase)
    db.get_record_by_id.return_value = augmented
    merge = Merge(db)

    assert merge._get_merged_concept_groups([subject]) == [(subject, {subject})]
    db.get_record_by_id.assert_called_once_with(
        subject,
        include_supplemental_mappings=True,
        apply_mapping_negations=True,
        as_condition=True,
    )
    merged, _ = merge._generate_merged_record({subject})
    assert merged.mappings == [broad]
    assert original.mappings[0].relation == Relation.EXACT_MATCH


def test_merge_preserves_mapping_predicates_and_provenance():
    mondo_id, ncit_id = "mondo:0005072", "ncit:C3270"
    target = "oncotree:OVT"
    exact = ConceptMapping(
        coding=concept_id_to_coding(target), relation=Relation.EXACT_MATCH
    )
    curated = [
        SssomMapping(
            subject_id=subject,
            object_id=target,
            predicate_id=Relation.BROAD_MATCH,
            mapping_justification="semapv:ManualMappingCuration",
            author_id=author,
        ).to_concept_mapping()
        for subject, author in [(ncit_id, "orcid:first"), (mondo_id, "orcid:second")]
    ]
    ncit = Condition(
        id=ncit_id, primaryCoding=concept_id_to_coding(ncit_id), mappings=[exact]
    )
    mondo = Condition(
        id=mondo_id,
        primaryCoding=concept_id_to_coding(mondo_id),
        mappings=[exact.model_copy(deep=True)],
    )
    records = {
        ncit_id: AbstractDatabase._with_supplemental_mappings(ncit, curated[:1]),
        mondo_id: AbstractDatabase._with_supplemental_mappings(mondo, curated),
    }
    db = Mock(spec=AbstractDatabase)
    db.get_record_by_id.side_effect = lambda record_id, **_: records.get(record_id)

    merged, _ = Merge(db)._generate_merged_record({mondo_id, ncit_id})

    assert [m for m in merged.mappings if m.coding.id == target] == [exact, *curated]
    assert records[ncit_id].mappings == [exact, curated[0]]


def test_get_merged_groups(
    mock_db: AbstractDatabase,
    merged_groups: dict[str, list[str]],
):
    """Test generation of merged groups"""
    m = Merge(mock_db)
    group_result = m._get_merged_concept_groups(
        # just do mondo IDs
        [
            "mondo:0005072",
            "mondo:0005233",
            "mondo:0002083",
            "mondo:0003587",
            "mondo:0004099",
            "mondo:0010648",
        ]
    )
    assert len(group_result) == 6
    group_result_grouped = {i[0]: i[1] for i in group_result}
    for normalized_id, mondo_id in (
        ("normalize.disease.ncit:C3270", "mondo:0005072"),
        ("normalize.disease.ncit:C2926", "mondo:0005233"),
        ("normalize.disease.ncit:C35424", "mondo:0002083"),
        ("normalize.disease.ncit:C8091", "mondo:0003587"),
        ("normalize.disease.ncit:C9012", "mondo:0004099"),
        ("normalize.disease.mondo:0010648", "mondo:0010648"),
    ):
        actual = group_result_grouped[mondo_id]
        expected = merged_groups[normalized_id]
        assert actual == set(expected)


def test_get_merged_groups_mondo_only(mock_db: AbstractDatabase):
    """Test generation of merged groups"""
    m = Merge(mock_db)
    with pytest.raises(ValueError, match="Only Mondo IDs"):
        _ = m._get_merged_concept_groups(
            [
                "mondo:0005072",
                "ncit:C2926",
            ]
        )


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
