from pathlib import Path

import deepdiff
from ga4gh.core.models import ConceptMapping, Relation
from ga4gh.va_spec.base import Condition, DataSet

from disease.database import AbstractDatabase
from disease.etl import base
from disease.etl.mappings import EtlMappings
from disease.etl.mondo import Mondo
from disease.schemas import SourceName, concept_id_to_coding


def test_mondo_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, Condition],
    sources: dict[str, DataSet],
):
    db = mock_db_class()
    etl = Mondo(db, test_data_dir / "mondo")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
    for id_key in (
        "mondo:0005072",
        "mondo:0002083",
        "mondo:0003587",
        "mondo:0004099",
        "mondo:0005233",
    ):
        expected = diseases[id_key]
        assert (
            deepdiff.DeepDiff(
                added_records[id_key],
                expected,
                ignore_order=True,
                report_repetition=True,
            )
            == {}
        )

    assert len(db._added_sources) == 1
    assert (
        deepdiff.DeepDiff(
            db._added_sources[SourceName.MONDO],
            sources[SourceName.MONDO],
            ignore_order=True,
        )
        == {}
    )


def test_run_specific_curation(mock_db_class, test_data_dir, monkeypatch):
    subject = "mondo:0005072"
    mapping = ConceptMapping(
        coding=concept_id_to_coding("ncit:C4207"), relation=Relation.EXACT_MATCH
    )
    bundled = EtlMappings({subject: [mapping]}, {})
    monkeypatch.setattr(base, "get_etl_mappings", lambda: bundled)
    db = mock_db_class()
    etl = Mondo(db, test_data_dir / "mondo")
    first_ids = etl.perform_etl(use_existing=True)
    assert db._added_supplemental_mappings[subject] == [mapping]

    assert (
        etl.perform_etl(use_existing=True, curated_mappings=EtlMappings({}, {}))
        == first_ids
    )
    assert db._added_supplemental_mappings[subject] == []

    injected = EtlMappings({}, {subject: [mapping]})
    assert etl.perform_etl(use_existing=True, curated_mappings=injected) == first_ids
    assert db._added_mapping_negations[subject] == [mapping]
