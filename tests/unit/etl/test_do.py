from pathlib import Path

import deepdiff
from ga4gh.core.models import Relation
from ga4gh.va_spec.base import Condition, DataSet

from disease.database import AbstractDatabase
from disease.etl.do import DO
from disease.schemas import SourceName


def test_do_etl(
    mock_db_class: type[AbstractDatabase],
    test_data_dir: Path,
    diseases: dict[str, Condition],
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

    (mapping,) = db._added_curated_mappings["DOID:6032"]
    assert mapping.coding.id == "ncit:C4207"
    assert mapping.relation == Relation.EXACT_MATCH
    assert {extension.name: extension.value for extension in mapping.extensions} == {
        "mapping_justification": "semapv:ManualMappingCuration",
        "author_id": "orcid:0000-0002-2568-6163",
    }
    assert not db._added_curated_mappings["DOID:769"]

    assert len(db._added_sources) == 1
    assert (
        deepdiff.DeepDiff(
            db._added_sources[SourceName.DO],
            sources[SourceName.DO],
            ignore_order=True,
        )
        == {}
    )
