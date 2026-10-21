from pathlib import Path

import deepdiff
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database.database import AbstractDatabase
from disease.etl.oncotree import OncoTree
from disease.schemas import SourceName


def test_oncotree_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, MappableConcept],
    datasets: dict[str, DataSet],
):
    db = mock_db_class()
    etl = OncoTree(db, test_data_dir / "oncotree")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
    for id_key in ("oncotree:NBL", "oncotree:NSCLC", "oncotree:ICPN"):
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
            db._added_sources[SourceName.ONCOTREE],
            datasets[SourceName.ONCOTREE],
            ignore_order=True,
        )
        == {}
    )
