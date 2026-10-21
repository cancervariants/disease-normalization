from pathlib import Path

import deepdiff
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.etl.mondo import Mondo
from disease.schemas import SourceName


def test_mondo_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, MappableConcept],
    datasets: dict[str, DataSet],
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
            datasets["mondo"],
            ignore_order=True,
        )
        == {}
    )
