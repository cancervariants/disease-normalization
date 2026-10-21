from pathlib import Path

import deepdiff
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.etl.omim import OMIM
from disease.schemas import SourceName


def test_omim_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, MappableConcept],
    datasets: dict[str, DataSet],
):
    db = mock_db_class()
    etl = OMIM(db, test_data_dir / "omim")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
    for id_key in ("MIM:309200", "MIM:613065", "MIM:247640"):
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
            db._added_sources[SourceName.OMIM],
            datasets[SourceName.OMIM],
            ignore_order=True,
        )
        == {}
    )
