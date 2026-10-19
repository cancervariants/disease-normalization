from pathlib import Path

import deepdiff
from ga4gh.core.models import Coding, Extension, MappableConcept, code, iriReference
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.etl.omim import OMIM
from disease.schemas import SourceName

fixtures = {
    "MIM:309200": MappableConcept(
        id="MIM:309200",
        conceptType="disease",
        primaryCoding=Coding(
            id="MIM:309200",
            system="https://omim.org/MIM:",
            code=code(root="309200"),
        ),
        name="MAJOR AFFECTIVE DISORDER 2",
        aliases=[
            "MAFD2",
            "MANIC-DEPRESSIVE ILLNESS",
            "MDI",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "MDX",
            "BIPOLAR AFFECTIVE DISORDER",
            "BPAD",
        ],
    ),
    "MIM:613065": MappableConcept(
        id="MIM:613065",
        name="LEUKEMIA, ACUTE LYMPHOBLASTIC",
        conceptType="disease",
        primaryCoding=Coding(
            id="MIM:613065",
            system="https://omim.org/MIM:",
            code=code(root="613065"),
        ),
        aliases=[
            "ALL",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO, 1",
            "ALL1",
            "LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1",
            "LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, T-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, B-HYPERDIPLOID, SUSCEPTIBILITY TO",
        ],
    ),
    "MIM:247640": MappableConcept(
        id="MIM:247640",
        name="LYMPHOBLASTIC LEUKEMIA, ACUTE, WITH LYMPHOMATOUS FEATURES",
        aliases=["LALL", "LYMPHOMATOUS ALL"],
        conceptType="disease",
        primaryCoding=Coding(
            id="MIM:247640",
            system="https://omim.org/MIM:",
            code=code(root="247640"),
        ),
    ),
}
expected_dataset = DataSet(
    name="OMIM",
    version="20240806",
    license=MappableConcept(
        name="custom",
        primaryCoding=Coding(
            code=code(root="OMIM-use-agreement"),
            system="https://omim.org",
            iris=[iriReference(root="https://omim.org/help/agreement")],
        ),
        extensions=[
            Extension(
                name="license_attributes",
                value={
                    "non_commercial": False,
                    "share_alike": True,
                    "attribution": True,
                },
            ),
        ],
    ),
    extensions=[
        Extension(
            name="data_url",
            value="https://www.omim.org/downloads",
        ),
        Extension(name="rdp_url", value="http://reusabledata.org/omim.html"),
    ],
)


def test_omim_etl(mock_etl_db: AbstractDatabase, test_data_dir: Path):
    etl = OMIM(mock_etl_db, test_data_dir / "omim")
    etl.perform_etl(use_existing=True)

    added_records = mock_etl_db._added_records
    for id_key, expected in fixtures.items():
        assert (
            deepdiff.DeepDiff(
                added_records[id_key],
                expected,
                ignore_order=True,
                report_repetition=True,
            )
            == {}
        )

    assert len(mock_etl_db._added_sources) == 1
    assert (
        deepdiff.DeepDiff(
            mock_etl_db._added_sources[SourceName.OMIM],
            expected_dataset,
            ignore_order=True,
        )
        == {}
    )
