from pathlib import Path

import deepdiff
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.etl.ncit import NCIt
from disease.schemas import SourceName


def test_ncit_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, MappableConcept],
    sources: dict[SourceName, DataSet],
):
    db = mock_db_class()
    etl = NCIt(db, test_data_dir / "ncit")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
    for id_key in ("ncit:C3270", "ncit:C2926"):
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
            db._added_sources[SourceName.NCIT],
            sources[SourceName.NCIT],
            ignore_order=True,
        )
        == {}
    )
