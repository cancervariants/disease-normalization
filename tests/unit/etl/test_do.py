from pathlib import Path

import deepdiff
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.etl.do import DO
from disease.schemas import SourceName


def test_do_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, MappableConcept],
    sources: dict[str, DataSet],
):
    db = mock_db_class()
    etl = DO(db, test_data_dir / "do")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
    for id_key in ("DOID:769", "DOID:5695", "DOID:1703", "DOID:6032"):
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
            db._added_sources[SourceName.DO],
            sources[SourceName.DO],
            ignore_order=True,
        )
        == {}
    )
